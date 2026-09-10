"""Ambiente de execução das migrações.

Escrito à mão, e não gerado por `alembic init`: o `alembic.ini` do
projeto já traz ajustes que o init sobrescreveria — o prefixo de data no
nome do arquivo, o hook do ruff e a ausência deliberada da URL do banco.

A URL vem de `settings.database_url`, como no resto da aplicação. Deixá-la
no `alembic.ini`, que é versionado, colocaria credenciais no repositório.
"""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import async_engine_from_config
from sqlalchemy.pool import NullPool

from app.config import settings
from app.persistence.tabelas import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Alvo do `--autogenerate`: o metadata das tabelas mapeadas.
target_metadata = Base.metadata

config.set_main_option("sqlalchemy.url", settings.database_url)


def incluir_objeto(objeto, nome, tipo, reflexo, objeto_comparado) -> bool:
    """Decide o que o autogenerate enxerga.

    O jobstore do APScheduler cria `apscheduler_jobs` sozinho, fora do
    metadata (ver rotinas/agendador.py). Como o autogenerate gera
    `drop_table` para tudo o que encontra no banco e não conhece no
    código, sem este filtro a primeira migração criada depois que o
    worker rodar apagaria a agenda inteira.
    """
    return not (tipo == "table" and nome == "apscheduler_jobs")


def migrar_offline() -> None:
    """Gera o SQL sem conectar ao banco (`alembic upgrade --sql`)."""
    context.configure(
        url=settings.database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=incluir_objeto,
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def _executar(conexao) -> None:
    context.configure(
        connection=conexao,
        target_metadata=target_metadata,
        include_object=incluir_objeto,
        # Sem isto, uma mudança de tipo de coluna passa despercebida pelo
        # autogenerate e o esquema diverge do modelo em silêncio.
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def migrar_online() -> None:
    """Aplica as migrações sobre uma conexão real.

    O driver é assíncrono e o Alembic é síncrono: `run_sync` é a ponte.
    `NullPool` porque o processo de migração é efêmero e não ganha nada
    em manter um pool aberto.
    """
    engine = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=NullPool,
    )

    async with engine.connect() as conexao:
        await conexao.run_sync(_executar)

    await engine.dispose()


if context.is_offline_mode():
    migrar_offline()
else:
    asyncio.run(migrar_online())
