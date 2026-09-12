"""Busca no índice vetorial pela linha de comando — critério de pronto da onda A.

Uso, a partir de `src/middleware`:

    python -m scripts.buscar_trechos "orçamento do Trecho Sul" --perfil lider_projeto --projetos PRJ-2024-018
    python -m scripts.buscar_trechos "periodicidade do relatório de status" --perfil membro_equipe

Não é RAG: não há modelo de geração nem prompt. Vetoriza a pergunta com
o mesmo e5 da indexação (prefixo `query:`), busca com o filtro de
permissão do escopo informado e imprime os trechos com o texto lido do
PostgreSQL. Serve para conferir o índice — e o filtro de permissão —
contra o serviço real, antes de o executor existir.
"""

import argparse
import asyncio
import sys

from app.persistence.sessao import encerrar, fabrica_de_sessoes
from app.rag.embeddings import codificar_consulta
from app.rag.ingestao.registro import RegistroIngestao, TrechoLido
from app.rag.vetorial.base import Acerto, Escopo
from app.rag.vetorial.fabrica import obter_repositorio_vetorial
from app.schemas.usuario import Perfil


async def _buscar(
    pergunta: str, escopo: Escopo, k: int
) -> tuple[tuple[Acerto, ...], dict[str, TrechoLido]]:
    vetor = codificar_consulta(pergunta)
    try:
        async with fabrica_de_sessoes()() as sessao:
            acertos = await obter_repositorio_vetorial(sessao).buscar(vetor, escopo=escopo, k=k)
            textos = await RegistroIngestao(sessao).textos([a.trecho_id for a in acertos])
    finally:
        await encerrar()
    return acertos, textos


def main(argv: list[str] | None = None) -> int:
    for fluxo in (sys.stdout, sys.stderr):
        if hasattr(fluxo, "reconfigure"):
            fluxo.reconfigure(encoding="utf-8")

    analisador = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    analisador.add_argument("pergunta")
    analisador.add_argument(
        "--perfil", choices=[perfil.value for perfil in Perfil], default=Perfil.DIRETORIA.value
    )
    analisador.add_argument(
        "--projetos", nargs="*", default=[], help="projetos do escopo (ignorados para a diretoria)"
    )
    analisador.add_argument("-k", type=int, default=5, help="trechos a recuperar (padrão: 5)")
    analisador.add_argument("--largura", type=int, default=400, help="caracteres de cada trecho")
    argumentos = analisador.parse_args(argv)

    escopo = Escopo(perfil=Perfil(argumentos.perfil), projetos=frozenset(argumentos.projetos))
    try:
        acertos, textos = asyncio.run(_buscar(argumentos.pergunta, escopo, argumentos.k))
    except RuntimeError as erro:
        print(f"erro: {erro}", file=sys.stderr)
        return 1

    if not acertos:
        print("nenhum trecho visível para este escopo")
        return 0
    for posicao, acerto in enumerate(acertos, start=1):
        print(f"{posicao}. {acerto.score:.4f}  {acerto.trecho_id}")
        lido = textos.get(acerto.trecho_id)
        if lido is None:
            # Vetor sem texto: a execução caiu entre o índice e o banco.
            print("   (sem texto no PostgreSQL — rode a ingestão de novo)")
            continue
        corpo = " ".join(lido.texto.split())
        reticencias = "…" if len(corpo) > argumentos.largura else ""
        print(f"   {lido.nome_arquivo} · {lido.localizador}")
        print(f"   {corpo[: argumentos.largura]}{reticencias}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
