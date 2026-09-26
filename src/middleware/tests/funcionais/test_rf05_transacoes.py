"""Casos TF-RF05-01 a TF-RF05-06 — transações no portfólio.

O fluxo de alteração com prévia e confirmação não existe no middleware atual.
Os casos executáveis permanecem como ``xfail`` estrito: deixam a lacuna visível
sem transformar funcionalidade futura em teste fictício aprovado.
"""

import importlib.util

import pytest

pytestmark = pytest.mark.xfail(
    strict=True,
    reason="fluxo transacional de portfólio com prévia e confirmação ainda não implementado",
)


def _modulo_transacional_existe() -> None:
    assert importlib.util.find_spec("app.portfolio.transacoes") is not None


def test_tf_rf05_01_grava_somente_apos_confirmacao() -> None:
    _modulo_transacional_existe()


def test_tf_rf05_02_negacao_preserva_valor_anterior() -> None:
    _modulo_transacional_existe()


def test_tf_rf05_03_sem_escrita_recusa_antes_de_ler_valor() -> None:
    _modulo_transacional_existe()


def test_tf_rf05_04_alteracao_registra_origem_autoria_e_momento() -> None:
    _modulo_transacional_existe()


def test_tf_rf05_05_falha_de_gravacao_nao_deixa_estado_parcial() -> None:
    _modulo_transacional_existe()


def test_tf_rf05_06_parametro_ausente_pede_complemento() -> None:
    _modulo_transacional_existe()
