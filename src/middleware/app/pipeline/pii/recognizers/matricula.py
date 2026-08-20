"""Reconhecedor de matrícula funcional do Metrô (exemplo de customização).

TODO (sprint técnica): confirmar com o parceiro o formato real da
matrícula e implementar o padrão correspondente.
"""

from app.pipeline.pii.detector import EntidadeSensivel


def reconhecer(texto: str) -> list[EntidadeSensivel]:
    """Localiza matrículas funcionais no texto."""
    raise NotImplementedError("Formato de matrícula a confirmar com o Metrô")
