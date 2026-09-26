"""Consumidor da fila `prata.webhooks.incoming` (Projeto.md 9.1.2.6 e 9.1.2.7).

Cada mensagem é um envelope `MensagemEvento` publicado pela rota de um
webhook, com o mesmo `message_id` do recebimento gravado no banco. O
processamento escolhe o tratador pelo `payload.provider` (`google_drive`,
`apps_script`) e segue a regra de entrega **at-least-once** idempotente:

1. uma trava de transação do PostgreSQL por `message_id`
   (`pg_advisory_xact_lock`) serializa duas entregas da mesma mensagem, e o
   recebimento é lido na mesma transação em que o tratador trabalha. Já
   processado: só `ack`, sem repetir o efeito — é o que torna inofensiva a
   reentrega. A trava não é na linha do recebimento de propósito: a rota
   marca `publicado_em` nessa linha logo depois de publicar, e um tratador
   demorado não pode segurá-la além do orçamento de 3 s da rota;
2. sucesso grava `processado_em` na mesma transação dos efeitos no banco
   e só depois confirma (`ack`). Uma queda entre o commit e o `ack` gera
   reentrega, que o passo 1 absorve;
3. `FalhaDefinitiva` (envelope inválido, recebimento desconhecido,
   provedor sem tratador, conflito de versão, escopo revogado) rejeita sem
   repor: o dead letter da fila leva a mensagem para `prata.failed`;
4. qualquer outra falha é transitória: a mensagem é republicada na fila de
   espera da tentativa seguinte (atraso crescente, ver `topologia.py`) e a
   original é confirmada. Esgotadas as `RABBITMQ_MAX_RETRIES`, vai para
   `prata.failed`.

A falha fica registrada no recebimento (tentativas e código, sem conteúdo
sensível) para quem inspecionar a fila de falhas.
"""

import asyncio
import logging
from collections.abc import Awaitable, Callable, Mapping
from datetime import UTC, datetime

import aio_pika
from aio_pika import DeliveryMode, Message
from aio_pika.abc import (
    AbstractExchange,
    AbstractIncomingMessage,
    AbstractQueue,
    AbstractRobustConnection,
)
from pydantic import ValidationError
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.mensageria.topologia import (
    EXCHANGE_RETENTATIVA,
    WEBHOOK_RECEBIDO,
    declarar_topologia,
    fila_retentativa,
)
from app.schemas.mensagem import MensagemEvento
from app.webhooks.repositorio import RecebimentoRepository
from app.webhooks.tabelas import RecebimentoTabela

logger = logging.getLogger(__name__)

CABECALHO_TENTATIVA = "x-tentativa"
ESPERA_RECONEXAO_SEGUNDOS = 10

Tratador = Callable[[MensagemEvento, AsyncSession], Awaitable[None]]


class FalhaDefinitiva(Exception):
    """Repetir não resolve: a mensagem vai para `prata.failed`."""

    def __init__(self, codigo: str) -> None:
        super().__init__(codigo)
        self.codigo = codigo


def _agora() -> datetime:
    return datetime.now(UTC)


class ConsumidorWebhooks:
    """Consome eventos de webhook e os entrega ao tratador do provedor."""

    def __init__(
        self,
        url: str,
        *,
        exchange: str,
        dead_letter_exchange: str,
        fabrica: async_sessionmaker[AsyncSession],
        tratadores: Mapping[str, Tratador],
        max_retries: int,
        prefetch: int,
        timeout_segundos: float = 5.0,
        relogio: Callable[[], datetime] = _agora,
    ) -> None:
        self._url = url
        self._exchange = exchange
        self._dead_letter = dead_letter_exchange
        self._fabrica = fabrica
        self._tratadores = dict(tratadores)
        self._max_retries = max_retries
        self._prefetch = prefetch
        self._timeout = timeout_segundos
        self._relogio = relogio
        self._conexao: AbstractRobustConnection | None = None
        self._fila: AbstractQueue | None = None
        self._retentativa: AbstractExchange | None = None
        self._etiqueta: str | None = None
        self._em_curso = 0
        self._ocioso = asyncio.Event()
        self._ocioso.set()

    async def iniciar(self) -> None:
        """Conecta, declara a topologia e começa a consumir com `prefetch` limitado."""
        conexao = await aio_pika.connect_robust(self._url, timeout=self._timeout)
        try:
            canal = await conexao.channel(publisher_confirms=True)
            await canal.set_qos(prefetch_count=self._prefetch)
            await declarar_topologia(canal, self._exchange, self._dead_letter)
            self._retentativa = await canal.get_exchange(EXCHANGE_RETENTATIVA)
            self._fila = await canal.get_queue(WEBHOOK_RECEBIDO.nome)
            self._etiqueta = await self._fila.consume(self.processar)
        except BaseException:
            await conexao.close()
            raise
        self._conexao = conexao
        logger.info("Consumidor de webhooks ativo (prefetch=%s)", self._prefetch)

    async def encerrar(self, prazo_segundos: float = 30.0) -> None:
        """Para de receber, espera a mensagem em curso e fecha a conexão."""
        if self._fila is not None and self._etiqueta is not None:
            try:
                await self._fila.cancel(self._etiqueta)
            except Exception:  # noqa: BLE001 — conexão já caída não impede o encerramento
                logger.warning("Cancelamento do consumo falhou; seguindo com o encerramento")
        try:
            await asyncio.wait_for(self._ocioso.wait(), timeout=prazo_segundos)
        except TimeoutError:
            logger.warning("Mensagem em curso não terminou em %ss", prazo_segundos)
        if self._conexao is not None:
            await self._conexao.close()
        self._conexao = self._fila = self._retentativa = self._etiqueta = None

    async def executar(self, encerramento: asyncio.Event) -> None:
        """Mantém o consumidor ativo até o encerramento, reconectando na subida.

        Broker fora do ar na subida vira nova tentativa a cada
        `ESPERA_RECONEXAO_SEGUNDOS`, e não um worker que não sobe; depois
        de conectado, a conexão robusta do aio-pika se recupera sozinha.
        """
        while not encerramento.is_set():
            try:
                await self.iniciar()
                break
            except Exception as erro:  # noqa: BLE001
                logger.warning("Consumidor sem broker (%s); nova tentativa", type(erro).__name__)
                try:
                    await asyncio.wait_for(encerramento.wait(), ESPERA_RECONEXAO_SEGUNDOS)
                except TimeoutError:
                    pass
        await encerramento.wait()
        await self.encerrar()

    async def processar(self, mensagem: AbstractIncomingMessage) -> None:
        """Processa uma mensagem e decide entre `ack`, retentativa e descarte."""
        self._em_curso += 1
        self._ocioso.clear()
        try:
            await self._processar(mensagem)
        finally:
            self._em_curso -= 1
            if self._em_curso == 0:
                self._ocioso.set()

    async def _processar(self, mensagem: AbstractIncomingMessage) -> None:
        try:
            evento = MensagemEvento.model_validate_json(mensagem.body)
        except ValidationError:
            logger.warning("Mensagem %s com envelope inválido descartada", mensagem.message_id)
            await mensagem.reject(requeue=False)
            return

        try:
            processado = await self._executar_tratador(evento)
        except FalhaDefinitiva as falha:
            logger.warning("Evento %s falhou em definitivo: %s", evento.message_id, falha.codigo)
            await self._registrar_falha(evento, falha.codigo)
            await mensagem.reject(requeue=False)
            return
        except Exception as erro:  # noqa: BLE001 — toda falha não classificada é transitória
            logger.warning(
                "Evento %s falhou (correlation_id=%s): %s",
                evento.message_id,
                evento.correlation_id,
                type(erro).__name__,
            )
            await self._registrar_falha(evento, "PROCESSAMENTO_TRANSITORIO")
            await self._tentar_de_novo(mensagem)
            return

        await mensagem.ack()
        if processado:
            logger.info(
                "Evento %s processado (correlation_id=%s)", evento.message_id, evento.correlation_id
            )

    async def _executar_tratador(self, evento: MensagemEvento) -> bool:
        """Roda o tratador na transação do recebimento; falso se já processado."""
        async with self._fabrica() as sessao:
            await sessao.execute(
                text("SELECT pg_advisory_xact_lock(hashtextextended(:chave, 0))"),
                {"chave": f"webhook:{evento.message_id}"},
            )
            recebimento = await sessao.scalar(
                select(RecebimentoTabela).where(
                    RecebimentoTabela.message_id == str(evento.message_id)
                )
            )
            if recebimento is None:
                raise FalhaDefinitiva("RECEBIMENTO_DESCONHECIDO")
            if recebimento.processado_em is not None:
                return False
            tratador = self._tratadores.get(str(evento.payload.get("provider")))
            if tratador is None:
                raise FalhaDefinitiva("PROVEDOR_SEM_TRATADOR")
            await tratador(evento, sessao)
            recebimento.processado_em = self._relogio()
            recebimento.erro_codigo = None
            await sessao.commit()
        return True

    async def _tentar_de_novo(self, mensagem: AbstractIncomingMessage) -> None:
        tentativa = int((mensagem.headers or {}).get(CABECALHO_TENTATIVA, 0)) + 1
        if tentativa > self._max_retries or self._retentativa is None:
            await mensagem.reject(requeue=False)
            return
        copia = Message(
            body=mensagem.body,
            content_type=mensagem.content_type,
            content_encoding=mensagem.content_encoding,
            delivery_mode=DeliveryMode.PERSISTENT,
            message_id=mensagem.message_id,
            correlation_id=mensagem.correlation_id,
            type=mensagem.type,
            app_id=mensagem.app_id,
            timestamp=mensagem.timestamp,
            headers={**(mensagem.headers or {}), CABECALHO_TENTATIVA: tentativa},
        )
        try:
            await self._retentativa.publish(
                copia,
                routing_key=fila_retentativa(WEBHOOK_RECEBIDO, tentativa),
                timeout=self._timeout,
            )
        except Exception:  # noqa: BLE001
            # Sem a cópia confirmada, a original não pode sumir: volta à fila.
            await mensagem.nack(requeue=True)
            return
        await mensagem.ack()

    async def _registrar_falha(self, evento: MensagemEvento, codigo: str) -> None:
        try:
            async with self._fabrica() as sessao:
                await RecebimentoRepository(sessao).registrar_falha(
                    str(evento.message_id), codigo=codigo
                )
                await sessao.commit()
        except Exception:  # noqa: BLE001 — o registro é diagnóstico, não bloqueia a decisão
            logger.warning("Não foi possível registrar a falha do evento %s", evento.message_id)
