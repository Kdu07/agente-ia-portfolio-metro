"""Produtor de eventos AMQP (Projeto.md, seção 9.1.2.6).

Publicar só é sucesso depois do `publisher confirm`: o chamador (endpoint
de áudio, webhook, agendador) responde `202` apenas quando o broker
assumiu o evento. Sem confirmação, `FalhaPublicacao` sobe com o
`message_id` e o `correlation_id` para o chamador responder erro
transitório e o cliente tentar de novo — o evento nunca é declarado
recebido sem estar no broker.

A mensagem é persistente e publicada com `mandatory`: um evento sem fila
ligada volta ao produtor em vez de ser descartado em silêncio pelo
exchange. Como isso só acontece com um `event_type` fora da topologia,
o tipo é conferido antes, e esse erro é de programação (`ValueError`),
não indisponibilidade.

A conexão é aberta no primeiro uso. A API sobe mesmo com o broker fora
do ar, e cada publicação tenta conectar de novo até conseguir; depois
disso, a conexão robusta do aio-pika se reconecta sozinha.

Os logs registram identificadores e o tipo do erro, nunca o payload nem
a URL, que carrega a senha.
"""

import asyncio
import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import aio_pika
from aio_pika import DeliveryMode, Message
from aio_pika.abc import AbstractExchange, AbstractRobustConnection
from aio_pika.exceptions import AMQPError, ChannelInvalidStateError

from app.config import Settings
from app.mensageria.topologia import FILAS_TRABALHO, declarar_topologia
from app.schemas.mensagem import MensagemEvento

logger = logging.getLogger(__name__)

EVENTOS_CONHECIDOS = frozenset(fila.chave for fila in FILAS_TRABALHO)

# Falhas do broker ou da rede. TimeoutError é subclasse de OSError.
_FALHAS_TRANSITORIAS = (AMQPError, ChannelInvalidStateError, OSError)


class FalhaPublicacao(Exception):
    """O broker não confirmou o evento; tratar como erro transitório."""

    def __init__(self, evento: MensagemEvento, motivo: str) -> None:
        super().__init__(f"Evento {evento.message_id} não confirmado pelo broker: {motivo}")
        self.message_id = evento.message_id
        self.correlation_id = evento.correlation_id
        self.motivo = motivo


def criar_evento(
    event_type: str,
    payload: dict[str, Any],
    *,
    correlation_id: UUID | None = None,
    producer: str = "middleware",
) -> MensagemEvento:
    """Monta o envelope com identificadores novos e data UTC.

    `correlation_id` vem da solicitação de origem quando ela já tem um;
    sem ele, o evento inaugura a correlação.
    """
    return MensagemEvento(
        message_id=uuid4(),
        event_type=event_type,
        schema_version=1,
        occurred_at=datetime.now(UTC),
        correlation_id=correlation_id or uuid4(),
        producer=producer,
        payload=payload,
    )


class ProdutorEventos:
    """Publica envelopes `MensagemEvento` no exchange de eventos."""

    def __init__(
        self,
        url: str,
        exchange: str,
        dead_letter_exchange: str,
        *,
        timeout_segundos: float = 5.0,
    ) -> None:
        self._url = url
        self._nome_exchange = exchange
        self._nome_dead_letter = dead_letter_exchange
        self._timeout = timeout_segundos
        self._conexao: AbstractRobustConnection | None = None
        self._exchange: AbstractExchange | None = None
        # Publicações concorrentes antes da primeira conexão abririam uma
        # conexão cada; a trava garante uma só.
        self._trava = asyncio.Lock()

    @classmethod
    def a_partir_de(cls, settings: Settings) -> "ProdutorEventos":
        return cls(
            settings.rabbitmq_url.get_secret_value(),
            settings.rabbitmq_exchange,
            settings.rabbitmq_dead_letter_exchange,
        )

    async def conectar(self) -> AbstractExchange:
        """Abre a conexão, o canal com confirmação e declara a topologia."""
        async with self._trava:
            if self._exchange is not None:
                return self._exchange
            conexao = await aio_pika.connect_robust(self._url, timeout=self._timeout)
            try:
                canal = await conexao.channel(publisher_confirms=True, on_return_raises=True)
                exchange = await declarar_topologia(
                    canal, self._nome_exchange, self._nome_dead_letter
                )
            except BaseException:
                await conexao.close()
                raise
            self._conexao, self._exchange = conexao, exchange
            return exchange

    async def publicar(self, evento: MensagemEvento) -> None:
        """Publica e aguarda a confirmação do broker.

        Levanta `ValueError` para tipo de evento sem fila e
        `FalhaPublicacao` quando o broker não confirma a tempo.
        """
        if evento.event_type not in EVENTOS_CONHECIDOS:
            raise ValueError(f"Tipo de evento sem fila na topologia: {evento.event_type}")

        mensagem = Message(
            body=evento.model_dump_json().encode("utf-8"),
            content_type="application/json",
            content_encoding="utf-8",
            delivery_mode=DeliveryMode.PERSISTENT,
            message_id=str(evento.message_id),
            correlation_id=str(evento.correlation_id),
            type=evento.event_type,
            app_id=evento.producer,
            timestamp=evento.occurred_at,
            headers={"schema_version": evento.schema_version},
        )
        try:
            exchange = await self.conectar()
            await exchange.publish(
                mensagem,
                routing_key=evento.event_type,
                mandatory=True,
                timeout=self._timeout,
            )
        except _FALHAS_TRANSITORIAS as erro:
            logger.warning(
                "Evento %s não confirmado (correlation_id=%s, tipo=%s): %s",
                evento.message_id,
                evento.correlation_id,
                evento.event_type,
                type(erro).__name__,
            )
            raise FalhaPublicacao(evento, type(erro).__name__) from erro

        logger.info(
            "Evento %s confirmado (correlation_id=%s, tipo=%s)",
            evento.message_id,
            evento.correlation_id,
            evento.event_type,
        )

    async def encerrar(self) -> None:
        """Fecha a conexão; a próxima publicação reconecta."""
        async with self._trava:
            conexao, self._conexao, self._exchange = self._conexao, None, None
        if conexao is not None:
            await conexao.close()
