"""Testes do registro persistente das rotinas no APScheduler."""

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.persistence.models import Rotina
from app.rotinas import agendador as modulo


def _rotina(
    *, rotina_id: str = "rotina-1", ativa: bool = True, agenda_cron: str = "0 8 * * mon-fri"
) -> Rotina:
    agora = datetime.now(UTC)
    return Rotina(
        id=rotina_id,
        nome="Resumo diário",
        prompt="Liste os riscos críticos dos projetos ativos",
        agenda_cron=agenda_cron,
        timezone="America/Sao_Paulo",
        dono_id="usuario-1",
        ativa=ativa,
        criada_em=agora,
        atualizada_em=agora,
        intencao_prevista="consultar_riscos",
    )


@pytest.fixture(autouse=True)
def _limpar_agendador(monkeypatch):
    monkeypatch.setattr(modulo, "_agendador", None)


def test_url_do_jobstore_preserva_dados_e_troca_driver():
    resultado = modulo._url_sincrona_jobstore(
        "postgresql+asyncpg://usuario:senha@db:5432/middleware"
    )

    assert resultado == "postgresql+psycopg://usuario:senha@db:5432/middleware"


def test_url_do_jobstore_traduz_ssl_do_asyncpg_para_sslmode():
    resultado = modulo._url_sincrona_jobstore(
        "postgresql+asyncpg://usuario:senha@psql.postgres.database.azure.com:5432/prata_dev"
        "?ssl=require"
    )

    assert resultado == (
        "postgresql+psycopg://usuario:senha@psql.postgres.database.azure.com:5432/prata_dev"
        "?sslmode=require"
    )


@pytest.mark.asyncio
async def test_registra_lista_substitui_e_remove_job():
    scheduler = AsyncIOScheduler(jobstores={"default": MemoryJobStore()}, timezone=UTC)
    modulo._agendador = scheduler
    scheduler.start(paused=True)
    try:
        rotina = _rotina()
        modulo.agendar(rotina)

        jobs = modulo.listar_agendadas()
        assert [job.id for job in jobs] == ["rotina:rotina-1"]
        assert str(jobs[0].trigger.timezone) == "America/Sao_Paulo"
        sexta = datetime(2026, 9, 18, 12, tzinfo=ZoneInfo("America/Sao_Paulo"))
        proximo_disparo = jobs[0].trigger.get_next_fire_time(None, sexta)
        assert proximo_disparo is not None
        assert proximo_disparo.weekday() == 0
        assert (proximo_disparo.hour, proximo_disparo.minute) == (8, 0)

        rotina.nome = "Resumo atualizado"
        modulo.agendar(rotina)
        assert modulo.listar_agendadas()[0].name == "Resumo atualizado"
        assert len(modulo.listar_agendadas()) == 1

        modulo.desagendar(rotina.id)
        modulo.desagendar(rotina.id)
        assert modulo.listar_agendadas() == []
    finally:
        scheduler.shutdown(wait=False)


@pytest.mark.parametrize("dia_semana", ["mon-fri", "1-5", "7"])
@pytest.mark.asyncio
async def test_job_sobrevive_reinicio_do_scheduler(tmp_path, dia_semana):
    url = f"sqlite:///{tmp_path / 'jobs.sqlite'}"

    primeiro = AsyncIOScheduler(
        jobstores={"default": SQLAlchemyJobStore(url=url)}, timezone=UTC
    )
    modulo._agendador = primeiro
    primeiro.start(paused=True)
    modulo.agendar(_rotina(agenda_cron=f"0 8 * * {dia_semana}"))
    primeiro.shutdown(wait=False)

    segundo = AsyncIOScheduler(
        jobstores={"default": SQLAlchemyJobStore(url=url)}, timezone=UTC
    )
    modulo._agendador = segundo
    segundo.start(paused=True)
    try:
        assert [job.id for job in modulo.listar_agendadas()] == ["rotina:rotina-1"]
        sexta = datetime(2026, 10, 9, 9, tzinfo=ZoneInfo("America/Sao_Paulo"))
        proximo = modulo.listar_agendadas()[0].trigger.get_next_fire_time(None, sexta)
        dia_esperado = 11 if dia_semana == "7" else 12
        assert proximo == datetime(2026, 10, dia_esperado, 8, tzinfo=sexta.tzinfo)
    finally:
        segundo.shutdown(wait=False)


@pytest.mark.parametrize(
    ("dia_semana", "dias_esperados"),
    [
        ("0", [6]),
        ("1", [0]),
        ("2", [1]),
        ("3", [2]),
        ("4", [3]),
        ("5", [4]),
        ("6", [5]),
        ("7", [6]),
        ("1-5", [0, 1, 2, 3, 4]),
        ("0-7", [6, 0, 1, 2, 3, 4, 5]),
        ("0-1", [6, 0]),
        ("5-7", [6, 4, 5]),
        ("0,7", [6]),
        ("0,1,5", [6, 0, 4]),
        ("1-5/2", [0, 2, 4]),
        ("1-7/2", [6, 0, 2, 4]),
        ("1/2", [6, 0, 2, 4]),
        ("*/2", [6, 1, 3, 5]),
        ("1,wed,5", [0, 2, 4]),
        ("sun", [6]),
        ("mon-fri", [0, 1, 2, 3, 4]),
        ("MON-FRI", [0, 1, 2, 3, 4]),
        ("*", [6, 0, 1, 2, 3, 4, 5]),
    ],
)
async def test_dias_do_job_seguem_cron_padrao(dia_semana, dias_esperados):
    scheduler = AsyncIOScheduler(jobstores={"default": MemoryJobStore()}, timezone=UTC)
    modulo._agendador = scheduler
    scheduler.start(paused=True)
    try:
        rotina = _rotina(agenda_cron=f"0 8 * * {dia_semana}")
        modulo.agendar(rotina)
        trigger = modulo.listar_agendadas()[0].trigger
        agora = datetime(2026, 10, 4, tzinfo=ZoneInfo(rotina.timezone))  # domingo
        anterior = None
        # Duas voltas conferem o intervalo inteiro e a passagem de semana.
        for dia in dias_esperados * 2:
            proximo = trigger.get_next_fire_time(anterior, agora)
            assert proximo is not None
            assert proximo.weekday() == dia
            assert (proximo.hour, proximo.minute) == (8, 0)
            assert str(proximo.tzinfo) == rotina.timezone
            anterior = proximo
            agora = proximo + timedelta(seconds=1)
        assert rotina.agenda_cron == f"0 8 * * {dia_semana}"
    finally:
        scheduler.shutdown(wait=False)
