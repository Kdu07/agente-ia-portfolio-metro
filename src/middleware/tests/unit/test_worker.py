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

    def add_listener(self, callback, mask: int) -> None:
        self.listener = callback
        self.mask = mask

    def resume(self) -> None:
        self.eventos.append("resume")

    def pause(self) -> None:
        self.eventos.append("pause")

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
        "pause",
        ("shutdown", False),
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


@pytest.mark.asyncio
async def test_worker_aguarda_rotina_em_curso_antes_de_fechar_pool(monkeypatch):
    agendador = AsyncIOScheduler(
        jobstores={"default": MemoryJobStore()},
        timezone=UTC,
    )
    eventos: list[str] = []
    encerrar = asyncio.Event()
    iniciou = asyncio.Event()
    liberar = asyncio.Event()

    monkeypatch.setattr(worker.sessao, "iniciar", lambda: None)

    async def fechar_banco() -> None:
        eventos.append("pool-fechado")

    async def disparar() -> None:
        eventos.append("rotina-inicio")
        iniciou.set()
        await liberar.wait()
        eventos.append("rotina-concluida")

    async def carregar() -> None:
        agendador.add_job(
            disparar,
            trigger=DateTrigger(run_date=datetime.now(UTC) + timedelta(milliseconds=20)),
        )

    monkeypatch.setattr(worker.sessao, "encerrar", fechar_banco)
    monkeypatch.setattr(worker, "criar_agendador", lambda: agendador)
    monkeypatch.setattr(worker, "carregar_agenda", carregar)

    processo = asyncio.create_task(worker.principal(evento_encerramento=encerrar))
    await asyncio.wait_for(iniciou.wait(), timeout=1)
    encerrar.set()
    await asyncio.sleep(0.05)

    assert "pool-fechado" not in eventos

    liberar.set()
    await asyncio.wait_for(processo, timeout=1)

    assert eventos == ["rotina-inicio", "rotina-concluida", "pool-fechado"]


@pytest.mark.asyncio
async def test_worker_cancela_rotina_apos_prazo_antes_de_fechar_pool(monkeypatch):
    agendador = AsyncIOScheduler(
        jobstores={"default": MemoryJobStore()},
        timezone=UTC,
    )
    eventos: list[str] = []
    encerrar = asyncio.Event()
    iniciou = asyncio.Event()

    monkeypatch.setattr(worker, "PRAZO_ENCERRAMENTO_SEGUNDOS", 0.01)
    monkeypatch.setattr(worker, "PRAZO_CANCELAMENTO_SEGUNDOS", 0.5)
    monkeypatch.setattr(worker.sessao, "iniciar", lambda: None)

    async def fechar_banco() -> None:
        eventos.append("pool-fechado")

    async def disparar() -> None:
        eventos.append("rotina-inicio")
        iniciou.set()
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            eventos.append("rotina-cancelada")
            raise

    async def carregar() -> None:
        agendador.add_job(
            disparar,
            trigger=DateTrigger(run_date=datetime.now(UTC) + timedelta(milliseconds=20)),
        )

    monkeypatch.setattr(worker.sessao, "encerrar", fechar_banco)
    monkeypatch.setattr(worker, "criar_agendador", lambda: agendador)
    monkeypatch.setattr(worker, "carregar_agenda", carregar)

    processo = asyncio.create_task(worker.principal(evento_encerramento=encerrar))
    await asyncio.wait_for(iniciou.wait(), timeout=1)
    encerrar.set()
    await asyncio.wait_for(processo, timeout=1)

    assert eventos == ["rotina-inicio", "rotina-cancelada", "pool-fechado"]
