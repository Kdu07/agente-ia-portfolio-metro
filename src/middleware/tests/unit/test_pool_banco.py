"""Testes da configuração explícita do pool PostgreSQL."""

from app.config import settings
from app.persistence import sessao


def test_engine_postgres_recebe_limites_configurados(monkeypatch) -> None:
    recebido = {}
    engine = object()

    def criar(url, **opcoes):
        recebido.update(url=url, **opcoes)
        return engine

    monkeypatch.setattr(settings, "database_url", "postgresql+asyncpg://teste")
    monkeypatch.setattr(settings, "database_pool_size", 7)
    monkeypatch.setattr(settings, "database_max_overflow", 4)
    monkeypatch.setattr(settings, "database_pool_timeout_seconds", 2.5)
    monkeypatch.setattr(sessao, "create_async_engine", criar)

    assert sessao.criar_engine() is engine
    assert recebido == {
        "url": "postgresql+asyncpg://teste",
        "pool_pre_ping": True,
        "pool_size": 7,
        "max_overflow": 4,
        "pool_timeout": 2.5,
    }


def test_engine_sqlite_nao_recebe_opcoes_incompativeis(monkeypatch) -> None:
    recebido = {}

    def criar(url, **opcoes):
        recebido.update(url=url, **opcoes)
        return object()

    monkeypatch.setattr(settings, "database_url", "sqlite+aiosqlite://")
    monkeypatch.setattr(sessao, "create_async_engine", criar)

    sessao.criar_engine()

    assert recebido == {"url": "sqlite+aiosqlite://", "pool_pre_ping": True}
