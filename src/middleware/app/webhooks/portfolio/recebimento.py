"""Recebimento dos eventos do portfólio: autenticar, validar, registrar e publicar.

Ordem da seção 9.1.2.7.2 do Projeto.md, "Entrada e autenticidade" e
"Respostas, duplicatas e publicação":

1. a assinatura HMAC e a janela de 300 s (`verificar_portfolio`, #388) vêm
   antes de interpretar o corpo, com o cadastro de chaves relido a cada
   entrega para refletir rotação e revogação;
2. JSON, schema, escopo da fonte e vínculo da entidade (`evento.py`);
3. o recebimento é gravado com a chave `source_id:event_id` e o hash dos
   bytes exatos do corpo. Repetição com o mesmo hash e já publicada: 204.
   Mesmo `event_id` com outro corpo: 409, preservando o original;
4. `webhook.received` com `provider=apps_script` e o evento validado, e
   `202` só depois do `publisher confirm` — o mesmo caminho do WH-01, e a
   mesma recuperação de pendentes no worker.

Tudo cabe no orçamento de 3 segundos; estourado, `503`.
"""

import asyncio
import hashlib
import logging
from collections.abc import Callable, Sequence
from datetime import UTC, datetime

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.auth.webhooks import WebhookRecusado, verificar_portfolio
from app.auth.webhooks_config import ErroConfiguracaoWebhook, carregar_chaves_portfolio
from app.mensageria.produtor import FalhaPublicacao, ProdutorEventos
from app.webhooks.drive.recebimento import publicar_recebimento
from app.webhooks.modelos import Provedor
from app.webhooks.portfolio.evento import autorizar, conferir_vinculo, ler_json, validar_evento
from app.webhooks.repositorio import FontePortfolioRepository, RecebimentoRepository

logger = logging.getLogger(__name__)

ORCAMENTO_SEGUNDOS = 3.0


def _agora() -> datetime:
    return datetime.now(UTC)


async def receber_evento(
    cabecalhos: Sequence[tuple[bytes, bytes]],
    corpo: bytes,
    *,
    chaves_arquivo: str,
    fabrica: async_sessionmaker[AsyncSession],
    produtor: ProdutorEventos,
    relogio: Callable[[], datetime] = _agora,
) -> int:
    """Processa um evento do emissor; devolve o status HTTP de sucesso.

    Recusas saem como `WebhookRecusado`. Cadastro de chaves ilegível,
    banco, broker ou orçamento indisponível viram `WebhookRecusado(503)`.
    """
    try:
        async with asyncio.timeout(ORCAMENTO_SEGUNDOS):
            return await _receber(cabecalhos, corpo, chaves_arquivo, fabrica, produtor, relogio)
    except (
        TimeoutError,
        SQLAlchemyError,
        OSError,
        FalhaPublicacao,
        ErroConfiguracaoWebhook,
    ) as erro:
        logger.warning("Evento do portfólio não aceito: %s", type(erro).__name__)
        raise WebhookRecusado(503, "WEBHOOK_INDISPONIVEL") from erro


async def _receber(
    cabecalhos: Sequence[tuple[bytes, bytes]],
    corpo: bytes,
    chaves_arquivo: str,
    fabrica: async_sessionmaker[AsyncSession],
    produtor: ProdutorEventos,
    relogio: Callable[[], datetime],
) -> int:
    chaves = carregar_chaves_portfolio(chaves_arquivo)
    fonte = verificar_portfolio(cabecalhos, corpo, chaves, agora=relogio().timestamp())
    evento = validar_evento(ler_json(corpo), fonte_autenticada=fonte)

    async with fabrica() as sessao:
        autorizar(evento, await FontePortfolioRepository(sessao).obter(fonte))
        await conferir_vinculo(sessao, evento)

    hash_corpo = hashlib.sha256(corpo).digest()
    async with fabrica() as sessao:
        recebimento, novo = await RecebimentoRepository(sessao).registrar(
            provedor=Provedor.APPS_SCRIPT,
            chave_externa=f"{evento.source_id}:{evento.event_id}",
            fonte_id=evento.source_id,
            canal_id=None,
            evento={"provider": Provedor.APPS_SCRIPT.value, "event": evento.model_dump()},
            agora=relogio(),
            corpo_sha256=hash_corpo,
        )
        await sessao.commit()

    if recebimento.corpo_sha256 != hash_corpo:
        # Mesmo `event_id`, outro conteúdo: o emissor não pode reescrever
        # um evento já aceito. O original fica como está.
        raise WebhookRecusado(409, "WEBHOOK_EVENTO_CONFLITANTE")
    if recebimento.publicado_em is not None:
        return 204

    await publicar_recebimento(recebimento, fabrica=fabrica, produtor=produtor, relogio=relogio)
    logger.info(
        "Evento do portfólio aceito (message_id=%s, correlation_id=%s, tipo=%s, repetido=%s)",
        recebimento.message_id,
        recebimento.correlation_id,
        evento.event_type,
        not novo,
    )
    return 202
