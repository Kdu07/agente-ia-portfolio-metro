"""Manutenção periódica do WH-01: pendentes e renovação de canais.

Roda no `worker`, e não na API, pela razão de sempre: a API pode ter
várias réplicas, e duas renovando o mesmo canal criariam canais demais.

- **Pendentes.** Um recebimento gravado sem publicação confirmada — o
  broker caiu, ou o processo morreu entre gravar e publicar — é
  republicado com os mesmos UUIDs. A seção 9.1.2.7.1 exige que isso
  rode após reinício e periodicamente, sem depender de o Google repetir.
  Só entram recebimentos mais velhos que `IDADE_MINIMA_PENDENTE`: os mais
  novos podem ser de uma requisição que ainda está publicando.
- **Renovação.** Ao atingir 80% da validade concedida, um canal novo é
  inscrito e ativado **antes** de o antigo ser encerrado; durante a
  transição os dois autenticam. O cursor salvo da fonte é preservado.

Cada ciclo registra a falha e segue: um broker fora do ar não pode
derrubar o worker, que também executa as rotinas.
"""

import asyncio
import logging
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.mensageria.produtor import FalhaPublicacao, ProdutorEventos
from app.webhooks.drive.inscricao import InscricaoDrive
from app.webhooks.drive.recebimento import publicar_recebimento
from app.webhooks.repositorio import CanalDriveRepository, RecebimentoRepository

logger = logging.getLogger(__name__)

# Bem acima do orçamento de 3 s da rota: nada que ainda esteja em curso.
IDADE_MINIMA_PENDENTE = timedelta(seconds=30)


def _agora() -> datetime:
    return datetime.now(UTC)


async def republicar_pendentes(
    fabrica: async_sessionmaker[AsyncSession],
    produtor: ProdutorEventos,
    *,
    relogio: Callable[[], datetime] = _agora,
    limite: int = 100,
) -> int:
    """Republica recebimentos sem confirmação; devolve quantos foram publicados.

    Para no primeiro que falhar: se o broker está fora do ar, insistir
    nos demais só multiplicaria tentativas contadas.
    """
    async with fabrica() as sessao:
        pendentes = await RecebimentoRepository(sessao).listar_pendentes(
            recebidos_antes=relogio() - IDADE_MINIMA_PENDENTE, limite=limite
        )
    publicados = 0
    for recebimento in pendentes:
        try:
            await publicar_recebimento(
                recebimento, fabrica=fabrica, produtor=produtor, relogio=relogio
            )
        except FalhaPublicacao:
            logger.warning(
                "Pendente %s continua sem confirmação; nova tentativa no próximo ciclo",
                recebimento.message_id,
            )
            break
        publicados += 1
    if publicados:
        logger.info("%s recebimento(s) pendente(s) republicado(s)", publicados)
    return publicados


async def renovar_canais(
    inscricao: InscricaoDrive,
    fabrica: async_sessionmaker[AsyncSession],
    *,
    relogio: Callable[[], datetime] = _agora,
) -> int:
    """Substitui os canais que passaram de 80% da validade; devolve quantos."""
    async with fabrica() as sessao:
        vencendo = await CanalDriveRepository(sessao).listar_para_renovar(agora=relogio())
    renovados = 0
    for canal_id in vencendo:
        novo = await inscricao.inscrever()
        await inscricao.encerrar(canal_id)
        logger.info("Canal %s substituído por %s", canal_id, novo.canal_id)
        renovados += 1
    return renovados


async def executar_manutencao(
    encerramento: asyncio.Event,
    *,
    fabrica: Callable[[], async_sessionmaker[AsyncSession]],
    produtor: ProdutorEventos,
    inscricao: Callable[[], InscricaoDrive | None],
    intervalo_segundos: float,
) -> None:
    """Executa um ciclo agora e repete a cada intervalo até o encerramento.

    `fabrica` e `inscricao` são montadas no primeiro ciclo, dentro do
    tratamento de falhas: um banco ou uma credencial indisponível na
    subida vira log e nova tentativa, e não um worker que não sobe.
    Sem inscrição (webhook do Drive não configurado neste ambiente), só
    os pendentes são tratados.
    """
    montados: tuple[async_sessionmaker[AsyncSession], InscricaoDrive | None] | None = None
    while not encerramento.is_set():
        try:
            if montados is None:
                montados = (fabrica(), inscricao())
            sessoes, drive = montados
            await republicar_pendentes(sessoes, produtor)
            if drive is not None:
                await renovar_canais(drive, sessoes)
        except Exception:
            logger.exception("Ciclo de manutenção dos webhooks falhou")
        try:
            await asyncio.wait_for(encerramento.wait(), timeout=intervalo_segundos)
        except TimeoutError:
            pass
