"""Integração real com Azure AI Content Safety.

Grava as fitas VHS para as operações do Content Safety:
- Categorias de conteúdo (text:analyze)

O serviço está configurado no tenant da equipe (g02) e as credenciais
estão disponíveis no ambiente de desenvolvimento.

Nota: Prompt Shields (text:shieldPrompt) requerem configuração adicional
do recurso e não foram gravados nesta sessão. As fitas atuais cobrem
apenas a análise de categorias de conteúdo.
"""

import os

import pytest

from app.config import settings
from app.pipeline.guardas.content_safety import Sessao, configurado, sessao

pytestmark = [pytest.mark.integracao, pytest.mark.externo]

ENDPOINT_GRAVADO = "https://content-safety-metrosp-g02.cognitiveservices.azure.com"


@pytest.fixture
async def sessao_content_safety(monkeypatch: pytest.MonkeyPatch):
    """Usa credencial real ao gravar e valores fictícios ao reproduzir.

    O VCR intercepta a requisição na reprodução. Os valores fictícios
    permitem que a fita rode sem `.env`, sem rede e sem segredo real.
    """
    if os.getenv("VHS_GRAVANDO"):
        if not configurado():
            pytest.skip("gravação exige CONTENT_SAFETY_ENDPOINT e CONTENT_SAFETY_KEY")
    else:
        monkeypatch.setattr(settings, "content_safety_endpoint", ENDPOINT_GRAVADO)
        monkeypatch.setattr(settings, "content_safety_key", "CHAVE-FICTICIA-PARA-VHS")

    async with sessao() as s:
        yield s


@pytest.mark.vcr
@pytest.mark.default_cassette("content_safety/analyze_texto_limpo")
async def test_analyze_texto_limpo(sessao_content_safety: Sessao) -> None:
    """Análise de categorias com texto legítimo não detecta violação."""
    corpo = {
        "text": "O projeto está no prazo e dentro do orçamento",
        "categories": ["Hate", "SelfHarm", "Sexual", "Violence"],
    }

    resposta = await sessao_content_safety.analisar("text:analyze", corpo)

    assert "categoriesAnalysis" in resposta
    # Nenhuma categoria deve ter severidade acima do limiar
    for categoria in resposta["categoriesAnalysis"]:
        assert categoria["severity"] == 0


@pytest.mark.vcr
@pytest.mark.default_cassette("content_safety/analyze_texto_odio")
async def test_analyze_texto_odio(sessao_content_safety: Sessao) -> None:
    """Análise de categorias detecta conteúdo de ódio."""
    corpo = {
        "text": "Pessoas desse grupo são inferiores e não merecem respeito",
        "categories": ["Hate", "SelfHarm", "Sexual", "Violence"],
    }

    resposta = await sessao_content_safety.analisar("text:analyze", corpo)

    assert "categoriesAnalysis" in resposta
    # Deve detectar a categoria Hate com severidade > 0
    hate_analysis = next(
        (c for c in resposta["categoriesAnalysis"] if c["category"] == "Hate"),
        None,
    )
    assert hate_analysis is not None
    assert hate_analysis["severity"] > 0
