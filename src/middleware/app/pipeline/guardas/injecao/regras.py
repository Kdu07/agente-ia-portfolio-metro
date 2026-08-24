"""Filtro de prompt injection por padrões conhecidos.

Primeira barreira: barata e determinística. Cobre ataques triviais
("ignore as instruções anteriores", tentativas de extrair o system
prompt, mudança de papel do agente). O que passar daqui ainda é
avaliado pelo classificador (classifier.py) — as duas camadas são
complementares, nenhuma substitui a outra.
"""

import re

# Padrões iniciais; expandir conforme testes adversariais da equipe.
PADROES_SUSPEITOS: list[re.Pattern] = [
    re.compile(r"ignore\s+(as\s+)?instru[cç][oõ]es\s+anteriores", re.IGNORECASE),
    re.compile(r"desconsidere\s+(as\s+)?regras", re.IGNORECASE),
    re.compile(r"(revele|mostre|imprima)\s+(seu|o)\s+(system\s+)?prompt", re.IGNORECASE),
    re.compile(r"voc[eê]\s+agora\s+[eé]\s+", re.IGNORECASE),
]


def contem_padrao_suspeito(texto: str) -> bool:
    """Retorna True se o texto casa com algum padrão conhecido de injection."""
    return any(padrao.search(texto) for padrao in PADROES_SUSPEITOS)
