"""Seleção do adaptador de modelo de linguagem por configuração.

Ponto único onde `settings.llm_backend` é lido, como
`vetorial/fabrica.py` é para o banco vetorial. Nenhum outro módulo de
`rag/` importa o SDK de um provedor de geração: é o que faz a troca de
modelo ser adaptador novo mais uma linha no `.env`.
"""

from app.config import settings
from app.rag.linguagem.base import ModeloLinguagem

BACKENDS = ("gemini", "openrouter")


def obter_modelo_linguagem() -> ModeloLinguagem:
    """Instancia o adaptador configurado."""
    backend = settings.llm_backend.strip().lower()

    if backend == "gemini":
        from app.rag.linguagem.gemini import ModeloGemini

        return ModeloGemini.de_configuracao()

    if backend == "openrouter":
        from app.rag.linguagem.openrouter import ModeloOpenRouter

        return ModeloOpenRouter.de_configuracao()

    raise ValueError(f"llm_backend inválido: {backend!r}. Esperado um de {BACKENDS}")
