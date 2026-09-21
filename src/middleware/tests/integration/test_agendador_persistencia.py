"""Persistência do APScheduler contra um PostgreSQL real."""

import asyncio
import uuid
from datetime import UTC, datetime

import pytest

from app.config import settings
from app.persistence.models import Rotina
from app.rotinas import agendador as modulo


@pytest.mark.integracao
@pytest.mark.asyncio
async def test_job_sobrevive_reinicio_com_postgresql(monkeypatch):
    rotina_id = f"teste-agenda-{uuid.uuid4().hex[:10]}"
    agora = datetime.now(UTC)
    rotina = Rotina(
        id=rotina_id,
        nome="Teste de persistência",
        prompt="Liste os projetos ativos",
        agenda_cron="0 8 * * *",
        timezone="America/Sao_Paulo",
        dono_id="usuario-teste",
        ativa=True,
        criada_em=agora,
        atualizada_em=agora,
        intencao_prevista="consultar_status_projeto",
    )
    monkeypatch.setattr(modulo, "_agendador", None)

    primeiro = modulo.criar_agendador()
    try:
        primeiro.start(paused=True)
    except Exception:  # noqa: BLE001 — indisponibilidade local pula a integração
        monkeypatch.setattr(modulo, "_agendador", None)
        pytest.skip(
            "PostgreSQL indisponível para o jobstore. Suba o banco do Compose."
        )

    try:
        modulo.agendar(rotina)
        primeiro.shutdown(wait=False)
        await asyncio.sleep(0)

        monkeypatch.setattr(modulo, "_agendador", None)
        segundo = modulo.criar_agendador()
        segundo.start(paused=True)
        try:
            assert segundo.get_job(f"rotina:{rotina_id}") is not None
            segundo.remove_job(f"rotina:{rotina_id}")
            segundo.remove_job(modulo.JOB_RECONCILIACAO_ID)
        finally:
            segundo.shutdown(wait=False)
            await asyncio.sleep(0)
    finally:
        monkeypatch.setattr(modulo, "_agendador", None)


def test_configuracao_aponta_jobstore_para_psycopg():
    url = modulo._url_sincrona_jobstore(settings.database_url)

    assert url.startswith("postgresql+psycopg://")
