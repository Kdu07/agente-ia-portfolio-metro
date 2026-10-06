"""Gatilho compartilhado para agendas com dias numéricos do cron padrão.

APScheduler 3 começa a semana na segunda. Converter para nomes antes de
construir o gatilho evita que validação, resposta HTTP e worker interpretem
a mesma agenda de maneiras diferentes. A expressão persistida é preservada.
"""

import re
from zoneinfo import ZoneInfo

from apscheduler.triggers.cron import CronTrigger

DIAS_CRON = ("sun", "mon", "tue", "wed", "thu", "fri", "sat", "sun")
ERRO_DIA_SEMANA = (
    "O dia da semana deve usar números de 0 a 7 (0 ou 7 = domingo, 1 = segunda), "
    "nomes de mon a sun, listas ou intervalos crescentes, como 1-5. "
    "Passos numéricos devem estar entre 1 e 7."
)


class DiaSemanaInvalido(ValueError):
    """Dia da semana fora do contrato aceito pela API de rotinas."""


def criar_gatilho_cron(agenda_cron: str, *, timezone: ZoneInfo) -> CronTrigger:
    """Interpreta 0/7 como domingo e 1-6 como segunda a sábado.

    Números, intervalos e passos são expandidos antes de converter cada dia:
    deslocar só os extremos de 0-1, por exemplo, criaria um intervalo invertido
    no APScheduler. Nomes continuam com a interpretação já usada pela tela.
    """
    campos = agenda_cron.split()
    if len(campos) != 5:
        raise ValueError("A agenda cron deve ter cinco campos.")
    campos[4] = _dias_nomeados(campos[4])
    return CronTrigger.from_crontab(" ".join(campos), timezone=timezone)


def _dias_nomeados(expressao: str) -> str:
    dias = []
    for item in expressao.split(","):
        if re.fullmatch(r"[a-z]{3}(?:-[a-z]{3})?", item, re.IGNORECASE):
            dias.append(item)
            continue

        numerico = re.fullmatch(r"(\*|[0-9]+(?:-[0-9]+)?)(?:/([0-9]+))?", item)
        if numerico is None:
            raise DiaSemanaInvalido(ERRO_DIA_SEMANA)
        intervalo, passo_texto = numerico.groups()
        passo = int(passo_texto) if passo_texto is not None else 1
        if intervalo == "*":
            inicio, fim = 0, 6
        elif "-" in intervalo:
            inicio, fim = map(int, intervalo.split("-"))
        else:
            inicio = int(intervalo)
            fim = 7 if passo_texto is not None else inicio

        if not (0 <= inicio <= fim <= 7 and 1 <= passo <= 7):
            raise DiaSemanaInvalido(ERRO_DIA_SEMANA)
        dias.extend(DIAS_CRON[dia] for dia in range(inicio, fim + 1, passo))

    return ",".join(dict.fromkeys(dias))
