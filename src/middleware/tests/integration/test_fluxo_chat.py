"""Teste de integração do fluxo completo do /chat.

Exercita a API de ponta a ponta com o Copilot MOCKADO — os testes de
integração nunca dependem do ambiente Microsoft real.

TODO (sprint técnica): habilitar quando o orquestrador for implementado.
"""

import pytest


@pytest.mark.skip(reason="Aguardando implementação do pipeline (sprints técnicas)")
def test_fluxo_completo_com_copilot_mockado() -> None:
    """Mensagem legítima atravessa o pipeline e recebe resposta do mock."""
