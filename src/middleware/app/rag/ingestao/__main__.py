"""`python -m app.rag.ingestao` — lê a pasta do Drive e indexa no banco vetorial.

    python -m app.rag.ingestao --simular     # lê, identifica, divide e tria; não grava nada
    python -m app.rag.ingestao               # indexa o que mudou desde a última execução
    python -m app.rag.ingestao --reindexar   # reindexa todos os documentos vigentes

A simulação não abre banco nem índice, e não vetoriza: é o ensaio que se
roda antes de gravar, para conferir no relatório o que vai entrar, o que
foi substituído e por quê.
"""

import argparse
import asyncio
import sys

from app.config import settings
from app.rag.ingestao.drive import FonteDrive
from app.rag.ingestao.indexacao import Ingestao, Relatorio


async def _executar(simular: bool, reindexar: bool) -> Relatorio:
    fonte = FonteDrive.de_configuracao()
    opcoes = {
        "limite": settings.chunk_tokens,
        "sobreposicao": settings.chunk_overlap,
        "namespace": settings.pinecone_namespace,
        "reindexar": reindexar,
    }
    if simular:
        return await Ingestao(
            fonte, registro=None, repositorio=None, confirmar=None, **opcoes
        ).executar()

    # Imports adiados: a simulação não deve exigir banco nem SDK do índice.
    from app.persistence.sessao import encerrar, fabrica_de_sessoes
    from app.rag.ingestao.registro import RegistroIngestao
    from app.rag.vetorial.fabrica import obter_repositorio_vetorial

    try:
        async with fabrica_de_sessoes()() as sessao:
            ingestao = Ingestao(
                fonte,
                registro=RegistroIngestao(sessao),
                repositorio=obter_repositorio_vetorial(sessao),
                confirmar=sessao.commit,
                **opcoes,
            )
            return await ingestao.executar()
    finally:
        await encerrar()


def main(argv: list[str] | None = None) -> int:
    # O console do Windows abre em cp1252 e não codifica os acentos do
    # relatório — mesmo tratamento de `rag/vetorial/provisionar.py`.
    for fluxo in (sys.stdout, sys.stderr):
        if hasattr(fluxo, "reconfigure"):
            fluxo.reconfigure(encoding="utf-8")

    analisador = argparse.ArgumentParser(
        prog="python -m app.rag.ingestao",
        description="Indexa o corpus da pasta controlada do Drive no banco vetorial.",
    )
    analisador.add_argument(
        "--simular",
        action="store_true",
        help="lê, identifica, divide e tria, sem vetorizar nem gravar nada",
    )
    analisador.add_argument(
        "--reindexar",
        action="store_true",
        help="reindexa todos os documentos vigentes, mesmo os que não mudaram",
    )
    argumentos = analisador.parse_args(argv)

    try:
        relatorio = asyncio.run(_executar(argumentos.simular, argumentos.reindexar))
    except RuntimeError as erro:
        # Configuração ausente (Drive, índice) chega aqui com a causa nomeada.
        print(f"erro: {erro}", file=sys.stderr)
        return 1
    print(relatorio.como_texto())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
