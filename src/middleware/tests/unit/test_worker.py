"""Testes do ciclo de vida do processo de agenda."""

import asyncio
from datetime import UTC, datetime, timedelta

import pytest
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger

from app import worker


class AgendadorEspiao:
    def __init__(self, eventos: list[object]) -> None:
        self.eventos = eventos
        self.running = False

    def start(self, *, paused: bool) -> None:
        self.eventos.append(("start", paused))
        self.running = True

    def resume(self) -> None:
        self.eventos.append("resume")

    def shutdown(self, *, wait: bool) -> None:
        self.eventos.append(("shutdown", wait))
        self.running = False


@pytest.mark.asyncio
async def test_worker_reconcilia_antes_de_liberar_e_encerra_ordenado(monkeypatch):
    eventos: list[object] = []
    agendador = AgendadorEspiao(eventos)
    encerrar = asyncio.Event()
    encerrar.set()

    monkeypatch.setattr(worker.sessao, "iniciar", lambda: eventos.append("banco-iniciar"))

    async def fechar_banco() -> None:
        eventos.append("banco-encerrar")

    async def carregar() -> None:
        eventos.append("carregar")

    monkeypatch.setattr(worker.sessao, "encerrar", fechar_banco)
    monkeypatch.setattr(worker, "criar_agendador", lambda: agendador)
    monkeypatch.setattr(worker, "carregar_agenda", carregar)

    await worker.principal(evento_encerramento=encerrar)

    assert eventos == [
        "banco-iniciar",
        ("start", True),
        "carregar",
        "resume",
        ("shutdown", True),
        "banco-encerrar",
    ]


@pytest.mark.asyncio
async def test_rotina_agendada_dispara_dentro_do_worker(monkeypatch):
    agendador = AsyncIOScheduler(
        jobstores={"default": MemoryJobStore()},
        timezone=UTC,
    )
    encerrar = asyncio.Event()
    disparou = asyncio.Event()

    monkeypatch.setattr(worker.sessao, "iniciar", lambda: None)

    async def fechar_banco() -> None:
        pass

    async def disparar() -> None:
        disparou.set()
        encerrar.set()

    async def carregar() -> None:
        agendador.add_job(
            disparar,
            trigger=DateTrigger(run_date=datetime.now(UTC) + timedelta(milliseconds=50)),
        )

    monkeypatch.setattr(worker.sessao, "encerrar", fechar_banco)
    monkeypatch.setattr(worker, "criar_agendador", lambda: agendador)
    monkeypatch.setattr(worker, "carregar_agenda", carregar)

    await asyncio.wait_for(
        worker.principal(evento_encerramento=encerrar),
        timeout=1,
    )

    assert disparou.is_set()
