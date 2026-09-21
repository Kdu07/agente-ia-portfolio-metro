"""Testes do registro persistente das rotinas no APScheduler."""

from datetime import UTC, datetime

import pytest
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.persistence.models import Rotina
from app.rotinas import agendador as modulo


def _rotina(*, rotina_id: str = "rotina-1", ativa: bool = True) -> Rotina:
    agora = datetime.now(UTC)
    return Rotina(
        id=rotina_id,
        nome="Resumo diário",
        prompt="Liste os riscos críticos dos projetos ativos",
        agenda_cron="0 8 * * 1-5",
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

        rotina.nome = "Resumo atualizado"
        modulo.agendar(rotina)
        assert modulo.listar_agendadas()[0].name == "Resumo atualizado"
        assert len(modulo.listar_agendadas()) == 1

        modulo.desagendar(rotina.id)
        modulo.desagendar(rotina.id)
        assert modulo.listar_agendadas() == []
    finally:
        scheduler.shutdown(wait=False)


@pytest.mark.asyncio
async def test_job_sobrevive_reinicio_do_scheduler(tmp_path):
    url = f"sqlite:///{tmp_path / 'jobs.sqlite'}"

    primeiro = AsyncIOScheduler(
        jobstores={"default": SQLAlchemyJobStore(url=url)}, timezone=UTC
    )
    modulo._agendador = primeiro
    primeiro.start(paused=True)
    modulo.agendar(_rotina())
    primeiro.shutdown(wait=False)

    segundo = AsyncIOScheduler(
        jobstores={"default": SQLAlchemyJobStore(url=url)}, timezone=UTC
    )
    modulo._agendador = segundo
    segundo.start(paused=True)
    try:
        assert [job.id for job in modulo.listar_agendadas()] == ["rotina:rotina-1"]
    finally:
        segundo.shutdown(wait=False)
