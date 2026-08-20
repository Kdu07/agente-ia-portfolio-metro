"""Classificador de prompt injection.

Segunda barreira, para ataques que as regras (rules.py) não pegam:
avaliação por modelo. Candidatos a implementação (decisão de stack na
Sprint 2): modelo dedicado (ex.: PromptGuard) ou LLM juiz de baixo
custo. A interface abaixo é estável independente da escolha.
"""

from dataclasses import dataclass


@dataclass
class ResultadoInjection:
    """Veredito do classificador sobre uma mensagem."""

    suspeita: bool
    confianca: float  # 0.0 a 1.0
    motivo: str  # descrição curta para auditoria


async def classificar(texto: str) -> ResultadoInjection:
    """Avalia se o texto é uma tentativa de prompt injection."""
    raise NotImplementedError("Modelo de detecção a definir na Sprint 2")
