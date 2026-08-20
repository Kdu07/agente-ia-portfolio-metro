"""Pseudonimização reversível de dados sensíveis.

Substitui cada entidade detectada por um placeholder (<PII_1>, <PII_2>...)
e devolve o mapeamento placeholder -> valor original, que fica retido
APENAS no middleware (armazenamento separado da auditoria). Assim o dado
real nunca sai do perímetro controlado, e a resposta do Copilot pode ser
desmascarada na volta quando necessário.
"""

from dataclasses import dataclass

from app.pipeline.pii.detector import EntidadeSensivel


@dataclass
class ResultadoMascaramento:
    """Texto mascarado + mapeamento para reversão."""

    texto_mascarado: str
    mapeamento: dict[str, str]  # ex.: {"<PII_1>": "123.456.789-00"}


def mascarar(texto: str, entidades: list[EntidadeSensivel]) -> ResultadoMascaramento:
    """Substitui as entidades por placeholders numerados."""
    raise NotImplementedError("A implementar nas sprints técnicas")


def desmascarar(texto: str, mapeamento: dict[str, str]) -> str:
    """Restaura os valores originais nos placeholders da resposta."""
    raise NotImplementedError("A implementar nas sprints técnicas")
