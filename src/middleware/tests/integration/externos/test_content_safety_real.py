"""Integração real com Azure AI Content Safety.

Grava as fitas VHS para as operações do Content Safety:
- Categorias de conteúdo (text:analyze)

O serviço está configurado no tenant da equipe (g02) e as credenciais
estão disponíveis no ambiente de desenvolvimento.

Nota: Prompt Shields (text:shieldPrompt) requerem configuração adicional
do recurso e não foram gravados nesta sessão. As fitas atuais cobrem
apenas a análise de categorias de conteúdo.
"""

import pytest

from app.config import settings
from app.pipeline.guardas.content_safety import Sessao, configurado, Indisponivel, sessao

pytestmark = pytest.mark.skipif(
    not configurado(),
    reason="exige CONTENT_SAFETY_ENDPOINT e CONTENT_SAFETY_KEY configurados",
)


@pytest.fixture
async def sessao_content_safety():
    """Sessão HTTP para chamadas ao Content Safety."""
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
