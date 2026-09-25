"""Regras de elegibilidade dos avisos do portfólio (Projeto.md 9.1.2.7.2).

Só alteração aplicada avisa; risco com severidade mínima avisa quando o
estado anterior **ou** o novo alcança o mínimo, inclusive numa redução; a
diferença leva só os campos que mudaram. A geração contra o banco está em
tests/integration/test_avisos_portfolio.py.
"""

from datetime import UTC, datetime

import pytest

from app.avisos.geracao import deve_avisar, diferencas, severidade
from app.avisos.modelos import PreferenciaAviso
from app.webhooks.modelos import ResultadoAplicacao, TipoEventoPortfolio
from app.webhooks.portfolio.aplicacao import Aplicacao

AGORA = datetime(2026, 9, 25, tzinfo=UTC)


def preferencia(tipo=TipoEventoPortfolio.RISCO, minimo=None) -> PreferenciaAviso:
    return PreferenciaAviso("u", "PRJ", tipo, True, minimo, AGORA)


def aplicacao(anteriores, novos, *, resultado=ResultadoAplicacao.APLICADO, tipo=None):
    return Aplicacao(
        resultado=resultado,
        source_id="fonte",
        event_id="e",
        event_type=tipo or TipoEventoPortfolio.RISCO,
        projeto_codigo="PRJ",
        entity_id="R",
        versao=2,
        anteriores=anteriores,
        novos=novos,
    )


def risco(probabilidade, impacto, status="monitorado"):
    return {"status": status, "probabilidade": probabilidade, "impacto": impacto}


def test_severidade_e_probabilidade_vezes_impacto():
    assert severidade(risco(4, 5)) == 20
    assert severidade({"status": "suspenso"}) is None


@pytest.mark.parametrize(
    "resultado",
    [
        ResultadoAplicacao.SEM_DIFERENCA,
        ResultadoAplicacao.REPETIDO,
        ResultadoAplicacao.IGNORADO_ANTIGO,
    ],
)
def test_so_alteracao_aplicada_avisa(resultado):
    assert not deve_avisar(preferencia(), aplicacao(risco(1, 1), risco(5, 5), resultado=resultado))


def test_sem_minimo_qualquer_alteracao_avisa():
    assert deve_avisar(preferencia(), aplicacao(risco(1, 1), risco(1, 2)))


@pytest.mark.parametrize(
    "antes,depois,avisa",
    [
        pytest.param(risco(3, 4), risco(5, 4), True, id="sobe e alcança o mínimo"),
        pytest.param(risco(5, 4), risco(2, 4), True, id="reduz a partir do mínimo"),
        pytest.param(risco(2, 4), risco(3, 3), False, id="fica abaixo antes e depois"),
        pytest.param(risco(5, 5), risco(5, 5, "mitigado"), True, id="só o status muda"),
    ],
)
def test_minimo_considera_o_estado_anterior_ou_o_novo(antes, depois, avisa):
    assert deve_avisar(preferencia(minimo=20), aplicacao(antes, depois)) is avisa


def test_minimo_nao_vale_para_outros_tipos():
    marco = aplicacao(
        {"status": "em_andamento"}, {"status": "atrasado"}, tipo=TipoEventoPortfolio.MARCO
    )

    assert deve_avisar(preferencia(TipoEventoPortfolio.MARCO, minimo=20), marco)


def test_diferencas_trazem_so_os_campos_alterados():
    assert diferencas(risco(3, 4), risco(5, 4)) == {"probabilidade": {"de": 3, "para": 5}}


def test_diferencas_de_data_real_preenchida():
    antes = {"status": "atrasado", "data_prevista": "2026-10-01", "data_real": None}
    depois = {"status": "concluido", "data_prevista": "2026-10-01", "data_real": "2026-09-30"}

    assert diferencas(antes, depois) == {
        "status": {"de": "atrasado", "para": "concluido"},
        "data_real": {"de": None, "para": "2026-09-30"},
    }
