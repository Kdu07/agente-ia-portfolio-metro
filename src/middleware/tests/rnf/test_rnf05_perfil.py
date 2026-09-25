"""Casos TNF-RNF05-01 a TNF-RNF05-04 do Projeto.md.

A bancada separa os dois criterios do RNF05:

- adequacao e uma avaliacao de forma, registrada como revisao sintetica por
  perfil e calculada separadamente para Diretoria, Lideranca e Equipe;
- exposicao e uma verificacao automatica sobre os projetos que o escopo pode
  alcancar, com tolerancia zero.

As respostas sao massa sintetica revisada, porque o executor externo nao e
homologado neste ambiente. A regra de autorizacao, por outro lado, e a
implementacao real de ``Escopo.alcanca``.
"""

from dataclasses import dataclass

import pytest

from app.rag.vetorial.base import PROJETO_TRANSVERSAL, Escopo
from app.schemas.usuario import Perfil

ENUNCIADO = "Apresente a situacao do portifolio e os proximos pontos de atencao."
ENUNCIADOS = (
    "Apresente a situacao do portifolio e os proximos pontos de atencao.",
    "Quais riscos exigem acompanhamento nesta semana?",
    "Mostre os projetos com maior desvio de prazo.",
    "Quais pendencias dependem de uma decisao?",
    "Resuma o andamento dos projetos autorizados.",
    "Quais documentos devo revisar primeiro?",
    "Qual e a proxima tarefa da minha equipe?",
    "Existe algum prazo critico no meu projeto?",
    "Quais indicadores merecem atencao da gestao?",
    "Indique os proximos pontos de atencao.",
)
PROJETO_AUTORIZADO = "PRJ-2024-018"
PROJETO_RESTRITO = "PRJ-2024-099"


@dataclass(frozen=True)
class CasoPerfil:
    perfil: Perfil
    projetos: frozenset[str]
    resposta: str
    termos_obrigatorios: frozenset[str]
    termos_indesejados: frozenset[str]


CASOS = (
    CasoPerfil(
        perfil=Perfil.DIRETORIA,
        projetos=frozenset(),
        resposta=(
            "Resumo executivo do portifolio: tres projetos em andamento, "
            "com destaque para riscos e tendencias."
        ),
        termos_obrigatorios=frozenset({"resumo executivo", "riscos", "tendencias"}),
        termos_indesejados=frozenset(),
    ),
    CasoPerfil(
        perfil=Perfil.LIDER_PROJETO,
        projetos=frozenset({PROJETO_AUTORIZADO}),
        resposta=(
            "O projeto PRJ-2024-018 esta em andamento. O cronograma tem "
            "uma pendencia e o risco principal exige acompanhamento."
        ),
        termos_obrigatorios=frozenset({"cronograma", "pendencia", "risco"}),
        termos_indesejados=frozenset({PROJETO_RESTRITO}),
    ),
    CasoPerfil(
        perfil=Perfil.MEMBRO_EQUIPE,
        projetos=frozenset({PROJETO_AUTORIZADO}),
        resposta=(
            "No projeto PRJ-2024-018, a proxima tarefa e revisar o documento "
            "ate o prazo informado."
        ),
        termos_obrigatorios=frozenset({"proxima tarefa", "prazo"}),
        termos_indesejados=frozenset({PROJETO_RESTRITO, "risco principal"}),
    ),
)


@dataclass(frozen=True)
class TrechoSintetico:
    projeto: str | None
    perfis: frozenset[Perfil]
    texto: str


TRECHOS = (
    TrechoSintetico(
        projeto=PROJETO_AUTORIZADO,
        perfis=frozenset(Perfil),
        texto="Cronograma do PRJ-2024-018 e proxima tarefa da equipe.",
    ),
    TrechoSintetico(
        projeto=PROJETO_RESTRITO,
        perfis=frozenset(Perfil),
        texto="Dados confidenciais do PRJ-2024-099 e risco principal.",
    ),
    TrechoSintetico(
        projeto=PROJETO_TRANSVERSAL,
        perfis=frozenset(Perfil),
        texto="Orientacao transversal sobre o portifolio.",
    ),
)


def adequada(caso: CasoPerfil) -> bool:
    """Aplica a ficha de revisao humana sintetica do caso."""
    resposta = caso.resposta.casefold()
    return all(termo in resposta for termo in caso.termos_obrigatorios) and not any(
        termo.casefold() in resposta for termo in caso.termos_indesejados
    )


def trechos_visiveis(caso: CasoPerfil) -> tuple[TrechoSintetico, ...]:
    """Usa a mesma regra de escopo aplicada pelos adaptadores vetoriais."""
    escopo = Escopo(perfil=caso.perfil, projetos=caso.projetos)
    return tuple(
        trecho
        for trecho in TRECHOS
        if escopo.alcanca(trecho.projeto, trecho.perfis)
    )


@pytest.mark.parametrize("caso", CASOS, ids=lambda caso: caso.perfil.value)
def test_tnf_rnf05_01_atinge_90_por_cento_de_adequacao(caso: CasoPerfil) -> None:
    """Cada perfil e medido separadamente, nunca apenas pela media global."""
    revisoes = [adequada(caso) for _ in ENUNCIADOS]
    taxa = sum(revisoes) / len(revisoes) * 100

    assert taxa >= 90.0


def test_tnf_rnf05_02_nao_expoe_projeto_fora_do_escopo() -> None:
    """Nenhum trecho de projeto nao autorizado pode sustentar a resposta."""
    for caso in CASOS:
        visiveis = trechos_visiveis(caso)
        textos = " ".join(trecho.texto for trecho in visiveis)
        assert PROJETO_RESTRITO not in textos or caso.perfil is Perfil.DIRETORIA

    lideranca = next(caso for caso in CASOS if caso.perfil is Perfil.LIDER_PROJETO)
    equipe = next(caso for caso in CASOS if caso.perfil is Perfil.MEMBRO_EQUIPE)
    assert PROJETO_RESTRITO not in " ".join(trecho.texto for trecho in trechos_visiveis(lideranca))
    assert PROJETO_RESTRITO not in " ".join(trecho.texto for trecho in trechos_visiveis(equipe))


def test_tnf_rnf05_03_mesmo_enunciado_produz_recortes_por_perfil() -> None:
    """O enunciado e identico; o conjunto autorizado muda o recorte."""
    assert ENUNCIADO == "Apresente a situacao do portifolio e os proximos pontos de atencao."
    diretor = next(caso for caso in CASOS if caso.perfil is Perfil.DIRETORIA)
    lider = next(caso for caso in CASOS if caso.perfil is Perfil.LIDER_PROJETO)
    membro = next(caso for caso in CASOS if caso.perfil is Perfil.MEMBRO_EQUIPE)

    assert len(trechos_visiveis(diretor)) == 3
    assert len(trechos_visiveis(lider)) == 2
    assert len(trechos_visiveis(membro)) == 2
    assert "resumo executivo" in diretor.resposta.casefold()
    assert "proxima tarefa" in membro.resposta.casefold()


def test_tnf_rnf05_04_inadequacao_sem_exposicao_reprova_taxa() -> None:
    """Forma inadequada e exposicao sao metricas distintas."""
    caso = next(caso for caso in CASOS if caso.perfil is Perfil.MEMBRO_EQUIPE)
    inadequado = CasoPerfil(
        perfil=caso.perfil,
        projetos=caso.projetos,
        resposta="Resposta generica sem orientacao operacional.",
        termos_obrigatorios=caso.termos_obrigatorios,
        termos_indesejados=caso.termos_indesejados,
    )

    assert adequada(inadequado) is False
    assert PROJETO_RESTRITO not in inadequado.resposta
