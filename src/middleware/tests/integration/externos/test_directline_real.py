"""Integração real com Direct Line do Copilot Studio.

Grava as fitas VHS para as operações do Direct Line:
- Iniciar conversa
- Postar activity
- Poll/stream de resposta

NOTA: Estes testes estão marcados como skip porque o cliente Direct Line
ainda não está implementado (app/copilot/client.py levanta NotImplementedError).
Quando o cliente estiver implementado e o DIRECTLINE_SECRET estiver configurado,
remova o skip e execute a gravação com VHS_GRAVANDO=1.

Timeout e respostas 401, 403 e 503 não pertencem ao VHS, porque não são
respostas de sucesso reutilizáveis. Esses casos devem usar MockTransport ou
respx quando o cliente existir, conforme Projeto.md 10.5.4.5.
"""

import pytest

from app.copilot.client import CopilotClient

pytestmark = [pytest.mark.integracao, pytest.mark.externo]


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

    primeira = await client.enviar(
        texto_mascarado="Qual o status do projeto?",
        intencao_id="consultar_status_projeto",
        exige_confirmacao=False,
        conversa_externa_id=None,
    )
    assert primeira.conversa_externa_id is not None

    resposta = await client.enviar(
        texto_mascarado="E o orçamento?",
        intencao_id="consultar_status_projeto",
        exige_confirmacao=False,
        conversa_externa_id=primeira.conversa_externa_id,
    )

    assert resposta.texto is not None
