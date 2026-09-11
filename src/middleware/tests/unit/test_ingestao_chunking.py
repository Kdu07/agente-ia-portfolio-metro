"""Testes da divisão em trechos (rag.ingestao.chunking).

O encoder é dublado como em test_embeddings_rag.py: o tokenizador falso
conta palavras, o que torna os orçamentos legíveis no próprio teste. O
que se afirma é o que, se quebrar, quebra em silêncio — trecho acima do
teto, linha de tabela cortada ao meio, trecho que mistura permissões.
"""

import numpy as np
import pytest

from app.pipeline.intencao.modelo import MODELO_EMBEDDINGS, EmbeddingsSentenca
from app.rag.embeddings import LIMITE_TOKENS
from app.rag.ingestao.chunking import dividir
from app.rag.ingestao.extracao import Unidade
from app.schemas.usuario import Perfil

TODOS = frozenset(Perfil)
CABECALHO = "PRJ-1 — Termo"  # 3 palavras


class EncoderFalso:
    """Tokeniza por espaço: um token por palavra."""

    def tokenize(self, textos) -> dict:
        return {"input_ids": np.zeros((len(textos), max(len(t.split()) for t in textos)))}


@pytest.fixture(autouse=True)
def encoder(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(EmbeddingsSentenca, "_encoders", {MODELO_EMBEDDINGS: EncoderFalso()})


def fixos(unidade: Unidade):
    return ("PRJ-1", TODOS)


def frase(i: int) -> Unidade:
    return Unidade(f"frase {i} com cinco palavras aqui", "7. PRAZO")  # 6 palavras


def linha(i: int, grupo: str = "aba Riscos") -> Unidade:
    return Unidade(f"ID: X{i} | A: a | B: b", grupo, indivisivel=True)  # 8 palavras


def corpo(texto: str) -> list[str]:
    """As linhas do trecho depois da linha de contexto e do grupo."""
    return texto.split("\n")[2:]


def test_trecho_abre_com_o_contexto_e_o_grupo() -> None:
    (trecho,) = dividir(
        [Unidade("Término: 30/06/2027", "7. PRAZO")],
        cabecalho=CABECALHO,
        metadados=fixos,
        limite=30,
        sobreposicao=0,
    )

    assert trecho.texto == "PRJ-1 — Termo\n7. PRAZO\nTérmino: 30/06/2027"
    assert trecho.localizador == "7. PRAZO"
    # A contagem guardada é a do encoder: prefixo `passage:` incluído.
    assert trecho.tokens == len(trecho.texto.split()) + 1


def test_nenhum_trecho_passa_do_orcamento() -> None:
    trechos = dividir(
        [frase(i) for i in range(20)],
        cabecalho=CABECALHO,
        metadados=fixos,
        limite=30,
        sobreposicao=0,
    )

    assert len(trechos) > 1
    assert all(len(t.texto.split()) <= 30 for t in trechos)


def test_trecho_nao_atravessa_grupo() -> None:
    trechos = dividir(
        [Unidade("uma", "1. A"), Unidade("duas", "2. B")],
        cabecalho=CABECALHO,
        metadados=fixos,
        limite=30,
        sobreposicao=0,
    )

    assert [t.localizador for t in trechos] == ["1. A", "2. B"]


def test_linha_de_tabela_nao_e_cortada_entre_trechos() -> None:
    linhas = [linha(i) for i in range(10)]

    trechos = dividir(linhas, cabecalho=CABECALHO, metadados=fixos, limite=30, sobreposicao=0)

    for unidade in linhas:
        assert sum(unidade.texto in corpo(t.texto) for t in trechos) == 1


def test_linha_maior_que_o_orcamento_e_partida_repetindo_o_identificador() -> None:
    enorme = Unidade(" | ".join(f"C{i}: v" for i in range(30)), "aba X", indivisivel=True)

    trechos = dividir([enorme], cabecalho=CABECALHO, metadados=fixos, limite=30, sobreposicao=0)

    assert len(trechos) > 1
    assert all(len(t.texto.split()) <= 30 for t in trechos)
    assert all(corpo(t.texto)[0].startswith("C0: v (cont.)") for t in trechos[1:])
    texto_total = " ".join(t.texto for t in trechos)
    assert all(f"C{i}: v" in texto_total for i in range(30))


def test_sobreposicao_so_vale_para_prosa() -> None:
    prosa = dividir(
        [frase(i) for i in range(6)],
        cabecalho=CABECALHO,
        metadados=fixos,
        limite=30,
        sobreposicao=6,
    )
    tabela = dividir(
        [linha(i, "7. PRAZO") for i in range(6)],
        cabecalho=CABECALHO,
        metadados=fixos,
        limite=30,
        sobreposicao=8,
    )

    assert corpo(prosa[1].texto)[0] == corpo(prosa[0].texto)[-1]
    assert corpo(tabela[1].texto)[0] != corpo(tabela[0].texto)[-1]


def test_permissoes_diferentes_nunca_dividem_o_mesmo_trecho() -> None:
    """Cada linha do consolidado leva a permissão da própria linha."""
    restrito = frozenset({Perfil.DIRETORIA})
    linhas = [
        Unidade("ID_PROJETO: PRJ-A", "aba Portfolio", True, {"ID_PROJETO": "PRJ-A"}),
        Unidade("ID_PROJETO: PRJ-B", "aba Portfolio", True, {"ID_PROJETO": "PRJ-B"}),
    ]

    trechos = dividir(
        linhas,
        cabecalho=CABECALHO,
        metadados=lambda u: (
            u.campos["ID_PROJETO"],
            restrito if u.campos["ID_PROJETO"] == "PRJ-B" else TODOS,
        ),
        limite=30,
        sobreposicao=0,
    )

    assert [(t.projeto, t.perfis) for t in trechos] == [("PRJ-A", TODOS), ("PRJ-B", restrito)]


def test_ordinais_comecam_em_um_e_sao_sequenciais() -> None:
    trechos = dividir(
        [frase(i) for i in range(20)],
        cabecalho=CABECALHO,
        metadados=fixos,
        limite=30,
        sobreposicao=0,
    )

    assert [t.ordinal for t in trechos] == list(range(1, len(trechos) + 1))


def test_orcamento_sem_folga_para_o_teto_e_recusado() -> None:
    with pytest.raises(ValueError, match="folga"):
        dividir(
            [frase(1)], cabecalho=CABECALHO, metadados=fixos, limite=LIMITE_TOKENS, sobreposicao=0
        )
