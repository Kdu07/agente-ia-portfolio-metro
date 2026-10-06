"""Validação e limites da conversão de dias numéricos do cron padrão."""

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from app.rotinas.cron import DiaSemanaInvalido, criar_gatilho_cron


@pytest.mark.parametrize(
    "dia_semana",
    ["8", "-1", "5-1", "1-8", "7-0", "*/0", "*/8", "1-5/0", "1,", "1foo", "mon-5"],
)
def test_dia_invalido_tem_mensagem_com_convencao_e_limites(dia_semana):
    with pytest.raises(DiaSemanaInvalido, match="0 ou 7 = domingo, 1 = segunda"):
        criar_gatilho_cron(f"0 8 * * {dia_semana}", timezone=ZoneInfo("UTC"))


@pytest.mark.parametrize("agenda", ["0 8 * *", "0 8 * * * *", "61 8 * * 1", "0 25 * * 1"])
def test_outros_campos_invalidos_continuam_recusados(agenda):
    with pytest.raises(ValueError):
        criar_gatilho_cron(agenda, timezone=ZoneInfo("UTC"))


def test_converter_dia_da_semana_preserva_demais_campos_e_fuso():
    fuso = ZoneInfo("America/Sao_Paulo")
    trigger = criar_gatilho_cron("  15  9\t5  1-12/2  *  ", timezone=fuso)
    proximo = trigger.get_next_fire_time(None, datetime(2026, 10, 4, tzinfo=fuso))
    assert proximo == datetime(2026, 11, 5, 9, 15, tzinfo=fuso)


def test_numeracao_do_mes_nao_e_deslocada_com_o_dia_da_semana():
    trigger = criar_gatilho_cron("0 8 5 10 1", timezone=ZoneInfo("UTC"))
    assert trigger.get_next_fire_time(None, datetime(2026, 10, 4, tzinfo=ZoneInfo("UTC"))) == (
        datetime(2026, 10, 5, 8, tzinfo=ZoneInfo("UTC"))
    )
