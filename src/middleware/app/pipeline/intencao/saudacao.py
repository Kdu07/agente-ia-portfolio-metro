"""Reconhecimento de saudação, antes do classificador de intenção.

O catálogo não tem classe de saudação, e o classificador manda "olá" para
`fora_de_escopo` com confiança alta. A recusa que sai daí ("essa
solicitação está fora do que eu faço") é a pior primeira impressão
possível para quem só abriu a conversa. A saudação é resolvida por regra,
e não por treino, porque o vocabulário é pequeno e fechado — e uma regra
determinística não desloca as métricas do classificador (RNF03).

A regra é estreita de propósito: só reconhece a mensagem que é
**inteiramente** cumprimento. "Olá, qual o status da Linha 6?" tem
pergunta e segue para o classificador; tratá-la como saudação engoliria
a pergunta.

**A saudação é registrada com a intenção reservada `INTENCAO`.** O
desfecho continua `recusada_fora_escopo`, porque o vocabulário de
desfechos é fechado e amarrado ao CHECK do banco, mas a intenção não pode
ficar nula: nula é também a recusa por escopo em que o classificador
devolveu um rótulo que o catálogo não reconhece. Com a marca explícita, a
interface deixa de etiquetar só a apresentação, e o painel de intenções
tira as saudações das contagens (`analytics.consultas._na_janela`). O
identificador não existe no catálogo e não tem chave estrangeira, como
todo `intencao_id` (ver `persistence/tabelas.py`).
"""

import re
import unicodedata
from itertools import pairwise

# Palavras que sozinhas já cumprimentam.
_NUCLEO = frozenset({"oi", "ola", "opa", "eai", "hello", "hi", "hey", "salve"})
# Pares que cumprimentam juntos, mas não separados ("boa" e "dia" não).
_PARES = frozenset({("bom", "dia"), ("boa", "tarde"), ("boa", "noite"), ("e", "ai")})
# O que pode acompanhar o cumprimento sem transformá-lo em pedido.
_COMPLEMENTOS = frozenset(
    {
        "bom",
        "boa",
        "dia",
        "tarde",
        "noite",
        "e",
        "ai",
        "tudo",
        "bem",
        "como",
        "vai",
        "voce",
        "vc",
        "esta",
        "ta",
        "td",
        "beleza",
        "blz",
        "prata",
        "pessoal",
    }
)
_MAX_PALAVRAS = 6

# Intenção gravada na interação de saudação. Fora do catálogo de propósito:
# nenhum classificador a devolve, só esta regra.
INTENCAO = "saudacao"


def _palavras(texto: str) -> list[str]:
    sem_acento = "".join(
        c for c in unicodedata.normalize("NFD", texto.casefold()) if not unicodedata.combining(c)
    )
    return re.findall(r"[a-z]+", sem_acento)


def e_saudacao(texto: str) -> bool:
    """True quando a mensagem só cumprimenta, sem pedir nada."""
    palavras = _palavras(texto)
    if not palavras or len(palavras) > _MAX_PALAVRAS:
        return False
    if any(p not in _NUCLEO and p not in _COMPLEMENTOS for p in palavras):
        return False
    tem_nucleo = any(p in _NUCLEO for p in palavras)
    tem_par = any(par in _PARES for par in pairwise(palavras))
    return tem_nucleo or tem_par
