"""Sincronização do corpus a partir das notificações do Drive (Projeto.md 9.1.2.7.1).

Tratador do provedor `google_drive` no consumidor (#394). A notificação só
diz que algo mudou; o que mudou vem de `changes.list`. Segue
"Processamento e atualização incremental do RAG":

1. a sincronização é serializada por fonte com uma trava de transação do
   PostgreSQL, compartilhada entre réplicas e liberada se o processo cair;
2. o cursor usado é o **persistido** para a fonte, nunca um vindo do
   callback. `changes.list` é percorrido por `nextPageToken` até o
   `newStartPageToken`, que fica provisório até a reindexação terminar;
3. havendo mudança, a ingestão incremental roda sobre a pasta controlada:
   ela compara a assinatura de cada documento e só reindexa o que mudou,
   inclusive exclusões e perda de acesso, e já filtra o que está fora da
   pasta. Uma página isolada de mudanças nunca é tratada como a lista
   completa de arquivos;
4. só então o cursor novo é gravado. Uma falha antes disso deixa o cursor
   antigo, e a nova tentativa relê as mesmas mudanças.

Várias notificações de uma mesma alteração (o Google envia algumas) viram
uma sincronização efetiva e outras que não encontram mudança nova.
"""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.mensageria.consumidor import FalhaDefinitiva
from app.schemas.mensagem import MensagemEvento
from app.webhooks.repositorio import SincronizacaoRepository

logger = logging.getLogger(__name__)

_CAMPOS = "nextPageToken,newStartPageToken,changes(fileId,removed)"


class SincronizacaoDrive:
    """Lê as mudanças desde o cursor salvo e reindexa o corpus."""

    def __init__(
        self,
        obter_servico: Callable[[], Any],
        *,
        reindexar: Callable[[], Awaitable[None]],
        relogio: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        """`obter_servico` é chamado no primeiro evento: sem credencial, o worker sobe."""
        self._obter_servico = obter_servico
        self._servico: Any = None
        self._reindexar = reindexar
        self._relogio = relogio

    async def tratar(self, evento: MensagemEvento, sessao: AsyncSession) -> None:
        fonte = str(evento.payload.get("fonte_id") or "")
        if not fonte:
            raise FalhaDefinitiva("PAYLOAD_INVALIDO")
        await sessao.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:chave, 0))"),
            {"chave": f"drive-sync:{fonte}"},
        )
        cursores = SincronizacaoRepository(sessao)
        cursor = await cursores.obter_cursor(fonte)
        if cursor is None:
            # Sem inscrição registrada não há de onde ler: não adianta repetir.
            raise FalhaDefinitiva("CURSOR_AUSENTE")

        if self._servico is None:
            self._servico = self._obter_servico()
        arquivos, novo_cursor = await asyncio.to_thread(self._listar_mudancas, cursor)
        if arquivos:
            logger.info("Drive: %s arquivo(s) alterado(s) na fonte %s", len(arquivos), fonte)
            await self._reindexar()
        await cursores.salvar_cursor(fonte, novo_cursor, agora=self._relogio())

    def _listar_mudancas(self, cursor: str) -> tuple[set[str], str]:
        """Percorre todas as páginas; devolve os IDs afetados e o cursor seguinte."""
        arquivos: set[str] = set()
        pagina: str | None = cursor
        while pagina is not None:
            resposta = (
                self._servico.changes()
                .list(
                    pageToken=pagina,
                    spaces="drive",
                    includeRemoved=True,
                    supportsAllDrives=True,
                    includeItemsFromAllDrives=True,
                    pageSize=1000,
                    fields=_CAMPOS,
                )
                .execute()
            )
            arquivos.update(
                mudanca["fileId"] for mudanca in resposta.get("changes", []) if "fileId" in mudanca
            )
            if "newStartPageToken" in resposta:
                return arquivos, str(resposta["newStartPageToken"])
            pagina = resposta.get("nextPageToken")
        raise RuntimeError("changes.list terminou sem newStartPageToken")


async def reindexar_corpus() -> None:
    """Ingestão incremental da pasta controlada, como `python -m app.rag.ingestao`."""
    # Imports adiados: SDK do índice e do Drive são do extra `rag`.
    from app.config import settings
    from app.persistence.sessao import fabrica_de_sessoes
    from app.rag.ingestao.drive import FonteDrive
    from app.rag.ingestao.indexacao import Ingestao
    from app.rag.ingestao.registro import RegistroIngestao
    from app.rag.vetorial.fabrica import obter_repositorio_vetorial

    async with fabrica_de_sessoes()() as sessao:
        relatorio = await Ingestao(
            FonteDrive.de_configuracao(),
            registro=RegistroIngestao(sessao),
            repositorio=obter_repositorio_vetorial(sessao),
            confirmar=sessao.commit,
            limite=settings.chunk_tokens,
            sobreposicao=settings.chunk_overlap,
            namespace=settings.pinecone_namespace,
            reindexar=False,
        ).executar()
    logger.info("Corpus reindexado após notificação do Drive:\n%s", relatorio.como_texto())
