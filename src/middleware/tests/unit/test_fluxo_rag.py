"""Testes do fluxo de RAG ponta a ponta (rag.fluxo), com todos os colaboradores dublados.

Os módulos já têm testes próprios; aqui se afirma a costura — que a
pergunta de quem pergunta, com o escopo de quem pergunta, atravessa
recuperação e geração e volta como resposta com fontes, e que a linha
de rastreabilidade registra identificadores e não conteúdo.
"""

import logging

import pytest

from app.rag.fluxo import FluxoRag
from app.rag.geracao import Gerador, Situacao
from app.rag.ingestao.registro import TrechoLido
from app.rag.recuperacao import Recuperador
from app.rag.vetorial.base import DIMENSAO, Acerto, Escopo
from app.schemas.usuario import Perfil

LIDER = Escopo(perfil=Perfil.LIDER_PROJETO, projetos=frozenset({"PRJ-2024-018"}))
TRECHO_ID = "PRJ-2024-018_TAP#0008"
TEXTO_DO_TRECHO = "8. CUSTO — Total estimado: R$ 847.900.000,00"


class RepositorioFalso:
    def __init__(self, acertos=()) -> None:
        self.buscas: list[dict] = []
        self._acertos = tuple(acertos)

    async def buscar(self, vetor, *, escopo, k, score_minimo=0.0):
        self.buscas.append({"escopo": escopo, "k": k})
        return self._acertos


class LeitorFalso:
    def __init__(self, *lidos: TrechoLido) -> None:
        self._lidos = {trecho.trecho_id: trecho for trecho in lidos}

    async def textos(self, trecho_ids):
        return {i: self._lidos[i] for i in trecho_ids if i in self._lidos}


class ModeloFalso:
    nome = "falso/v1"

    def __init__(self, resposta: str = "Resposta [1].") -> None:
        self.chamadas: list[dict] = []
        self._resposta = resposta

    async def gerar(self, *, instrucoes: str, conteudo: str) -> str:
        self.chamadas.append({"instrucoes": instrucoes, "conteudo": conteudo})
        return self._resposta


def trecho_do_tap() -> TrechoLido:
    return TrechoLido(
        trecho_id=TRECHO_ID,
        documento_id="PRJ-2024-018_TAP",
        texto=TEXTO_DO_TRECHO,
        localizador="8. CUSTO",
        nome_arquivo="PRJ-2024-018_TAP_v3_20250822.docx",
        link=None,
        projeto="PRJ-2024-018",
        perfis=frozenset({Perfil.DIRETORIA, Perfil.LIDER_PROJETO}),
    )


def fluxo(acertos, lidos, modelo: ModeloFalso) -> tuple[FluxoRag, RepositorioFalso]:
    repositorio = RepositorioFalso(acertos)
    recuperador = Recuperador(
        repositorio,
        LeitorFalso(*lidos),
        k=5,
        score_minimo=0.75,
        codificar=lambda texto: tuple(0.1 for _ in range(DIMENSAO)),
    )
    return FluxoRag(recuperador, Gerador(modelo)), repositorio


async def test_pergunta_vira_resposta_com_fontes() -> None:
    modelo = ModeloFalso("O custo total estimado é R$ 847.900.000,00 [1].")
    rag, repositorio = fluxo([Acerto(TRECHO_ID, 0.87)], [trecho_do_tap()], modelo)

    resultado = await rag.responder("Qual o custo do Trecho Sul?", LIDER)

    assert resultado.resposta.situacao is Situacao.RESPONDIDA
    assert resultado.resposta.fontes[0].trecho == TEXTO_DO_TRECHO
    assert resultado.recuperacao.trechos[0].trecho_id == TRECHO_ID
    assert repositorio.buscas[0]["escopo"] is LIDER
    assert TEXTO_DO_TRECHO in modelo.chamadas[0]["conteudo"]


async def test_contexto_da_conversa_vai_so_para_a_geracao() -> None:
    modelo = ModeloFalso("O custo total estimado e R$ 847.900.000,00 [1].")
    rag, _ = fluxo([Acerto(TRECHO_ID, 0.87)], [trecho_do_tap()], modelo)
    pergunta_atual = "E qual e o custo?"
    contexto = "Historico: falavamos do Trecho Sul.\nPergunta atual: E qual e o custo?"

    resultado = await rag.responder(
        pergunta_atual,
        LIDER,
        pergunta_para_geracao=contexto,
    )

    assert resultado.recuperacao.consulta == pergunta_atual
    assert contexto in modelo.chamadas[0]["conteudo"]


async def test_pergunta_sem_trecho_visivel_nao_chega_ao_modelo() -> None:
    """O caso da Expansão Leste para quem não é da diretoria: o índice não
    devolve nada, e o modelo não tem chance de responder de memória."""
    modelo = ModeloFalso()
    rag, _ = fluxo([], [], modelo)

    resultado = await rag.responder("Qual o orçamento da Expansão Leste?", LIDER)

    assert resultado.resposta.situacao is Situacao.SEM_CONTEXTO
    assert modelo.chamadas == []


async def test_rastreabilidade_registra_ids_e_nao_texto(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO, logger="app.rag.fluxo")
    rag, _ = fluxo(
        [Acerto(TRECHO_ID, 0.87)], [trecho_do_tap()], ModeloFalso("R$ 847.900.000,00 [1].")
    )

    await rag.responder("Qual o custo do Trecho Sul?", LIDER)

    registro = caplog.text
    assert "situacao=respondida" in registro
    assert TRECHO_ID in registro
    assert "perfil=lider_projeto" in registro
    assert "847.900.000" not in registro
    assert "Trecho Sul" not in registro  # nem a pergunta
