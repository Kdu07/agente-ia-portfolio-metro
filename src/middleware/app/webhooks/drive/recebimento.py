"""Recebimento das notificações do Drive: autenticar, registrar e publicar.

Segue a ordem da seção 9.1.2.7.1 do Projeto.md, "Resposta ao provedor":

1. autenticar antes de consultar a deduplicação ou produzir qualquer
   efeito: `verificar_drive` (#388) contra o canal cadastrado, com o
   recurso confirmado na inscrição, nunca o que veio no callback;
2. `sync` e estados que o contrato não processa terminam em `204`, sem
   registro nem publicação;
3. `change` vira um recebimento durável, gravado e confirmado **antes** da
   publicação, com os UUIDs do evento interno atribuídos uma única vez;
4. a publicação de `webhook.received` só é sucesso com o `publisher
   confirm`; então `publicado_em` é gravado e a resposta é `202`.

Uma repetição já publicada recebe `204`. Uma repetição ainda pendente
tenta publicar de novo com os mesmos identificadores — nunca `204` só
porque o registro existe. Sem confirmação, o recebimento fica pendente
para a recuperação (commit 4) e o Google recebe `503`, que o faz repetir.

Tudo isso cabe no orçamento de 3 segundos; estourado, `503`.
"""

import asyncio
import logging
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.auth.webhooks import WebhookRecusado
from app.auth.webhooks_drive import verificar_drive
from app.mensageria.produtor import FalhaPublicacao, ProdutorEventos
from app.mensageria.topologia import WEBHOOK_RECEBIDO
from app.schemas.mensagem import MensagemEvento
from app.webhooks.modelos import Provedor, Recebimento
from app.webhooks.repositorio import CanalDriveRepository, RecebimentoRepository

logger = logging.getLogger(__name__)

ORCAMENTO_SEGUNDOS = 3.0
_ESTADOS_SEM_TRABALHO = frozenset({"sync"})


def _agora() -> datetime:
    return datetime.now(UTC)


def _cabecalho(cabecalhos: Sequence[tuple[bytes, bytes]], nome: bytes) -> str | None:
    """Primeiro valor ASCII do cabeçalho; a validação completa é de `verificar_drive`."""
    for chave, valor in cabecalhos:
        if chave.lower() == nome:
            try:
                return valor.decode("ascii")
            except UnicodeDecodeError:
                return None
    return None


def evento_interno(recebimento: Recebimento) -> MensagemEvento:
    """Envelope de 9.1.2.6 com os UUIDs estáveis do recebimento."""
    return MensagemEvento(
        message_id=UUID(recebimento.message_id),
        event_type=WEBHOOK_RECEBIDO.chave,
        schema_version=1,
        occurred_at=recebimento.recebido_em,
        correlation_id=UUID(recebimento.correlation_id),
        producer="middleware",
        payload=recebimento.evento,
    )


async def publicar_recebimento(
    recebimento: Recebimento,
    *,
    fabrica: async_sessionmaker[AsyncSession],
    produtor: ProdutorEventos,
    relogio: Callable[[], datetime] = _agora,
) -> None:
    """Publica o evento do recebimento e marca `publicado_em`.

    Levanta `FalhaPublicacao` sem confirmação, depois de contar a
    tentativa. Compartilhada com a recuperação de pendentes.
    """
    try:
        await produtor.publicar(evento_interno(recebimento))
    except FalhaPublicacao:
        async with fabrica() as sessao:
            await RecebimentoRepository(sessao).registrar_falha(
                recebimento.message_id, codigo="PUBLICACAO_NAO_CONFIRMADA"
            )
            await sessao.commit()
        raise
    async with fabrica() as sessao:
        await RecebimentoRepository(sessao).marcar_publicado(
            recebimento.message_id, agora=relogio()
        )
        await sessao.commit()


async def receber_notificacao(
    cabecalhos: Sequence[tuple[bytes, bytes]],
    corpo: bytes,
    *,
    fabrica: async_sessionmaker[AsyncSession],
    produtor: ProdutorEventos,
    fonte_id: str,
    relogio: Callable[[], datetime] = _agora,
) -> int:
    """Processa uma notificação; devolve o status HTTP de sucesso.

    Recusas saem como `WebhookRecusado`, com o status e o código do
    contrato. Indisponibilidade do banco, do broker ou do orçamento vira
    `WebhookRecusado(503)`.
    """
    try:
        async with asyncio.timeout(ORCAMENTO_SEGUNDOS):
            return await _receber(cabecalhos, corpo, fabrica, produtor, fonte_id, relogio)
    except (TimeoutError, SQLAlchemyError, OSError, FalhaPublicacao) as erro:
        logger.warning("Notificação do Drive não aceita: %s", type(erro).__name__)
        raise WebhookRecusado(503, "WEBHOOK_INDISPONIVEL") from erro


async def _receber(
    cabecalhos: Sequence[tuple[bytes, bytes]],
    corpo: bytes,
    fabrica: async_sessionmaker[AsyncSession],
    produtor: ProdutorEventos,
    fonte_id: str,
    relogio: Callable[[], datetime],
) -> int:
    canal_id = _cabecalho(cabecalhos, b"x-goog-channel-id")
    canal = None
    if canal_id:
        async with fabrica() as sessao:
            canal = await CanalDriveRepository(sessao).obter_para_verificacao(canal_id)
    canais = {canal_id: canal} if canal_id and canal else {}
    notificacao = verificar_drive(
        cabecalhos, corpo, canais, fonte=fonte_id, agora=relogio().timestamp()
    )

    if notificacao.estado in _ESTADOS_SEM_TRABALHO:
        return 204
    if not notificacao.processar:
        # Estado novo com origem e formato válidos: ignorado, e a
        # reconciliação de recuperação continua disponível.
        logger.warning("Estado do Drive não suportado ignorado: %s", notificacao.estado)
        return 204

    if canal is None:  # verificar_drive só aceita canal cadastrado
        raise WebhookRecusado(401, "WEBHOOK_NAO_AUTORIZADO")
    evento = {
        "provider": Provedor.GOOGLE_DRIVE.value,
        "fonte_id": notificacao.fonte,
        "channel_id": notificacao.canal_id,
        "resource_id": canal.recurso_id,
        "resource_state": notificacao.estado,
        "message_number": notificacao.numero,
    }
    async with fabrica() as sessao:
        recebimento, novo = await RecebimentoRepository(sessao).registrar(
            provedor=Provedor.GOOGLE_DRIVE,
            chave_externa=f"{notificacao.canal_id}:{notificacao.numero}",
            fonte_id=notificacao.fonte,
            canal_id=notificacao.canal_id,
            evento=evento,
            agora=relogio(),
        )
        await sessao.commit()

    if recebimento.publicado_em is not None:
        return 204

    await publicar_recebimento(recebimento, fabrica=fabrica, produtor=produtor, relogio=relogio)
    logger.info(
        "Notificação do Drive aceita (message_id=%s, correlation_id=%s, repetida=%s)",
        recebimento.message_id,
        recebimento.correlation_id,
        not novo,
    )
    return 202
