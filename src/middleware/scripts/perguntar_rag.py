"""Pergunta ao RAG pela linha de comando — recuperação, geração e fontes.

Uso, a partir de `src/middleware`:

    python -m scripts.perguntar_rag "Qual o custo total do Trecho Sul?" --perfil lider_projeto --projetos PRJ-2024-018
    python -m scripts.perguntar_rag "Quem aprova mudança de 15% no orçamento?" --perfil membro_equipe
    python -m scripts.perguntar_rag "..." --trechos     # mostra também o que foi recuperado

Diferente de `scripts.buscar_trechos`, aqui há modelo de geração: é o
fluxo inteiro de `app/rag/fluxo.py`, contra o índice, o PostgreSQL e o
provedor configurados no `.env`. Serve para conferir uma pergunta
isolada; a medição sobre o conjunto de referência é a bancada
(`python -m app.rag.bancada`).
"""

import argparse
import asyncio
import sys

from app.persistence.sessao import encerrar, fabrica_de_sessoes
from app.rag.fluxo import ResultadoRag, montar_fluxo
from app.rag.linguagem.base import ErroGeracao
from app.rag.vetorial.base import Escopo
from app.schemas.usuario import Perfil


async def _perguntar(pergunta: str, escopo: Escopo) -> ResultadoRag:
    try:
        async with fabrica_de_sessoes()() as sessao:
            return await montar_fluxo(sessao).responder(pergunta, escopo)
    finally:
        await encerrar()


def _imprimir(resultado: ResultadoRag, mostrar_trechos: bool, largura: int) -> None:
    resposta = resultado.resposta
    print(resposta.texto)
    print()
    print(
        f"situação: {resposta.situacao.value} · modelo: {resposta.modelo or '(não chamado)'} · "
        f"{resultado.latencia_ms} ms"
    )
    for numero, fonte in enumerate(resposta.fontes, start=1):
        print(f"[{numero}] {fonte.documento} · {fonte.localizador} · score {fonte.score:.4f}")
        if fonte.link:
            print(f"    {fonte.link}")

    recuperacao = resultado.recuperacao
    if recuperacao.sem_texto or recuperacao.fora_do_escopo:
        print(
            f"atenção: {recuperacao.sem_texto} vetor(es) sem texto e "
            f"{recuperacao.fora_do_escopo} fora do escopo no PostgreSQL — rode a ingestão de novo"
        )
    if mostrar_trechos:
        print("\ntrechos recuperados:")
        for posicao, trecho in enumerate(recuperacao.trechos, start=1):
            corpo = " ".join(trecho.texto.split())
            reticencias = "…" if len(corpo) > largura else ""
            print(f"{posicao}. {trecho.score:.4f}  {trecho.trecho_id}")
            print(f"   {corpo[:largura]}{reticencias}")


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
    analisador.add_argument(
        "--trechos", action="store_true", help="mostra os trechos recuperados, citados ou não"
    )
    analisador.add_argument("--largura", type=int, default=300, help="caracteres de cada trecho")
    argumentos = analisador.parse_args(argv)

    escopo = Escopo(perfil=Perfil(argumentos.perfil), projetos=frozenset(argumentos.projetos))
    try:
        resultado = asyncio.run(_perguntar(argumentos.pergunta, escopo))
    except (RuntimeError, ValueError) as erro:
        # Configuração ausente, consulta vazia e ErroGeracao chegam aqui.
        prefixo = "modelo indisponível" if isinstance(erro, ErroGeracao) else "erro"
        print(f"{prefixo}: {erro}", file=sys.stderr)
        return 1

    _imprimir(resultado, argumentos.trechos, argumentos.largura)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
