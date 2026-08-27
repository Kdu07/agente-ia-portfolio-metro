"""Testes dos conjuntos de treino e teste do classificador.

O que se verifica aqui não é código, é o **corpus**: um conjunto de dados
com vazamento entre treino e teste produz métrica inflada, e nenhuma
leitura do código revelaria isso. Como o RNF03 é apurado sobre esses
arquivos, as invariantes abaixo são pré-condição da evidência.
"""

import pytest

from app.pipeline.intencao import catalogo, dados
from app.pipeline.intencao.dados import Origem


@pytest.fixture(scope="module")
def treino() -> list:
    return dados.carregar_treino()


@pytest.fixture(scope="module")
def teste() -> list:
    return dados.carregar_teste()


def test_conjuntos_nao_estao_vazios(treino: list, teste: list) -> None:
    assert len(treino) > 1000
    assert len(teste) > 400


def test_todo_rotulo_existe_no_catalogo(treino: list, teste: list) -> None:
    """Um rótulo fora do catálogo é classe fantasma.

    O orquestrador resolve o id previsto contra o catálogo; treinar uma
    classe que ele não conhece produz um modelo capaz de emitir um rótulo
    que o pipeline sempre descarta.
    """
    for enunciado in treino + teste:
        assert catalogo.esta_no_catalogo(enunciado.intencao_id), enunciado.intencao_id


def test_catalogo_inteiro_esta_representado_no_treino(treino: list) -> None:
    """Nenhuma classe do catálogo pode ficar sem exemplo de treino."""
    assert set(dados.distribuicao(treino)) == set(catalogo.CATALOGO)


def test_nao_ha_vazamento_entre_treino_e_teste(treino: list, teste: list) -> None:
    """Nenhum enunciado do teste pode aparecer no treino.

    É a invariante que sustenta o RNF03: um único enunciado repetido dos
    dois lados já mede memorização em vez de generalização.
    """
    normalizar = lambda e: e.texto.strip().lower()
    comuns = {normalizar(e) for e in treino} & {normalizar(e) for e in teste}
    assert not comuns, f"enunciados em ambos os conjuntos: {sorted(comuns)[:5]}"


def test_nao_ha_enunciado_com_dois_rotulos(treino: list, teste: list) -> None:
    """O mesmo texto com rótulos diferentes é ruído irrecuperável.

    Nenhum modelo acerta os dois, e o erro entra na matriz de confusão
    como se fosse falha do classificador.
    """
    rotulos: dict[str, set[str]] = {}
    for enunciado in treino + teste:
        rotulos.setdefault(enunciado.texto.strip().lower(), set()).add(
            enunciado.intencao_id
        )
    conflitos = {texto: r for texto, r in rotulos.items() if len(r) > 1}
    assert not conflitos, f"conflitos: {list(conflitos.items())[:3]}"


def test_teste_combina_as_duas_origens(teste: list) -> None:
    """O conjunto de teste precisa manter as duas procedências distinguíveis.

    Acertar o corpus sintético é acertar o gerador de templates; acertar
    o CSV do catálogo é generalizar. A bancada reporta os dois.
    """
    origens = {e.origem for e in teste}
    assert origens == {Origem.SINTETICO, Origem.CATALOGO}
    assert sum(e.origem is Origem.CATALOGO for e in teste) == 67


def test_treino_cobre_texto_degradado(treino: list) -> None:
    """O corpus precisa conter variação ruidosa, não só forma canônica.

    O canal de voz introduz erro em siglas e códigos (risco R03), e um
    modelo treinado só em texto limpo degrada exatamente ali.
    """
    ruidosos = sum(e.e_ruidoso for e in treino)
    assert ruidosos / len(treino) > 0.3


def test_split_desconhecido_falha_alto() -> None:
    """Nome de split errado não pode virar conjunto vazio silencioso."""
    with pytest.raises(ValueError, match="split desconhecido"):
        dados.carregar_corpus("validacao")
