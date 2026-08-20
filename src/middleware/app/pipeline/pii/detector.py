"""Detecção de dados sensíveis no texto do usuário.

Combina NER + regras (candidato: Microsoft Presidio com spaCy pt-BR)
para localizar CPF, e-mail, telefone, valores contratuais etc. Os
reconhecedores específicos do Metrô (matrícula, código de contrato)
vivem em recognizers/ e são registrados aqui.
"""

from dataclasses import dataclass


@dataclass
class EntidadeSensivel:
    """Uma ocorrência de dado sensível localizada no texto."""

    tipo: str  # ex.: "CPF", "EMAIL", "MATRICULA"
    inicio: int  # offset inicial no texto
    fim: int  # offset final no texto
    valor: str  # trecho original (nunca persistir sem mascarar)


def detectar(texto: str) -> list[EntidadeSensivel]:
    """Localiza todas as entidades sensíveis presentes no texto."""
    raise NotImplementedError("Integração com Presidio/spaCy pendente (Sprint 2)")
