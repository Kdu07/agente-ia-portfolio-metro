"""Casos TF-RF07-01 a TF-RF07-03 — análise comparativa fora do MVP."""

import pytest

pytestmark = pytest.mark.skip(
    reason="RF07 está explicitamente fora do MVP e sem tópico no executor (Projeto.md 10.1.4.1)"
)


def test_tf_rf07_01_compara_projetos_autorizados() -> None:
    pass


def test_tf_rf07_02_relaciona_risco_entre_projetos() -> None:
    pass


def test_tf_rf07_03_agregado_nao_revela_projeto_alheio() -> None:
    pass
