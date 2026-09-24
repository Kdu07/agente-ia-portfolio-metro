"""Integração real com Direct Line do Copilot Studio.

Grava as fitas VHS para as operações do Direct Line:
- Iniciar conversa
- Postar activity
- Poll/stream de resposta

NOTA: Este teste está marcado como skip porque o cliente Direct Line
ainda não está implementado (app/copilot/client.py levanta NotImplementedError).
Quando o cliente estiver implementado e o DIRECTLINE_SECRET estiver configurado,
remova o skip e execute a gravação com VHS_GRAVANDO=1.
"""

import pytest

from app.config import settings
from app.copilot.client import CopilotClient

pytestmark = pytest.mark.skipif(
    not settings.directline_secret,
    reason="exige DIRECTLINE_SECRET configurado",
)


@pytest.mark.skip(reason="Cliente Direct Line ainda não implementado")
@pytest.mark.vcr
@pytest.mark.default_cassette("directline/iniciar_conversa")
async def test_iniciar_conversa() -> None:
    """Inicia uma nova conversa com o Copilot Studio via Direct Line."""
    client = CopilotClient()

    # Primeira mensagem inicia a conversa
    resposta = await client.enviar(
        texto_mascarado="Qual o status do projeto?",
        intencao_id="consultar_status_projeto",
        exige_confirmacao=False,
        conversa_externa_id=None,
    )

    assert resposta.conversa_externa_id is not None
    assert resposta.texto is not None


@pytest.mark.skip(reason="Cliente Direct Line ainda não implementado")
@pytest.mark.vcr
@pytest.mark.default_cassette("directline/turno_seguinte")
async def test_turno_seguinte() -> None:
    """Envia mensagem em conversa existente."""
    client = CopilotClient()

    resposta = await client.enviar(
        texto_mascarado="E o orçamento?",
        intencao_id="consultar_status_projeto",
        exige_confirmacao=False,
        conversa_externa_id="conversa-existente-id",
    )

    assert resposta.texto is not None


@pytest.mark.skip(reason="Cliente Direct Line ainda não implementado")
@pytest.mark.vcr
@pytest.mark.default_cassette("directline/timeout")
async def test_timeout() -> None:
    """Verifica tratamento de timeout ao exceder COPILOT_TIMEOUT_SECONDS."""
    client = CopilotClient()

    # Simula timeout usando endpoint que não responde
    resposta = await client.enviar(
        texto_mascarado="teste de timeout",
        intencao_id="teste",
        exige_confirmacao=False,
    )

    # Timeout deve ser tratado e devolver erro adequado
    assert resposta.erro is not None


@pytest.mark.skip(reason="Cliente Direct Line ainda não implementado")
@pytest.mark.vcr
@pytest.mark.default_cassette("directline/erro_servico")
async def test_erro_servico() -> None:
    """Verifica tratamento de erro devolvido pelo serviço (401, 403, 503)."""
    client = CopilotClient()

    resposta = await client.enviar(
        texto_mascarado="teste de erro",
        intencao_id="teste",
        exige_confirmacao=False,
    )

    # Erro de serviço deve ser tratado e devolver erro adequado
    assert resposta.erro is not None
