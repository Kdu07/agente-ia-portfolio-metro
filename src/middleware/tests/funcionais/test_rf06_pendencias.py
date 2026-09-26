"""Casos TF-RF06-01 a TF-RF06-05 — alertas proativos de pendências."""

import importlib.util

import pytest

pytestmark = pytest.mark.xfail(
    strict=True,
    reason="varredura e entrega proativa de pendências estão planejadas para a Onda 5",
)


def _sonda_de_pendencias_existe() -> None:
    assert importlib.util.find_spec("app.rotinas.pendencias") is not None


def test_tf_rf06_01_varredura_alerta_responsavel() -> None:
    _sonda_de_pendencias_existe()


def test_tf_rf06_02_contato_parte_do_sistema() -> None:
    _sonda_de_pendencias_existe()


def test_tf_rf06_03_projeto_completo_nao_gera_alerta() -> None:
    _sonda_de_pendencias_existe()


def test_tf_rf06_04_alerta_chega_somente_ao_responsavel() -> None:
    _sonda_de_pendencias_existe()


def test_tf_rf06_05_resposta_ao_alerta_retorna_ao_fluxo_transacional() -> None:
    _sonda_de_pendencias_existe()
