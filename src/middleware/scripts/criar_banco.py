"""Cria o esquema do banco, aplicando as migrações até a última versão.

Uso, a partir de `src/middleware`:

    python -m scripts.criar_banco
    python -m scripts.criar_banco --versao head   # equivalente ao padrão
    python -m scripts.criar_banco --conferir      # só relata, não altera

**Por que isto não cria tabela nenhuma por conta própria.** Seria mais
curto chamar `Base.metadata.create_all()` aqui, e seria um erro: o banco
passaria a ter dois caminhos de criação, e eles divergiriam na primeira
migração que alterasse uma coluna. Quem sabe criar o esquema é o
Alembic; este script só o invoca com uma verificação de conexão antes e
um relatório depois, para que a falha mais comum — banco no ar, mas
inalcançável — apareça com essa cara, e não como um traceback de driver.
"""

import argparse
import asyncio
import sys
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text

from app.config import settings
from app.persistence.sessao import criar_engine

RAIZ = Path(__file__).resolve().parent.parent
ALEMBIC_INI = RAIZ / "alembic.ini"

# Os schemas fora do padrão, na ordem em que as migrações os criaram.
# A mesma lista que o `migrations/env.py` reconhece no autogenerate.
ESQUEMAS = ("rag", "portfolio", "webhook")


def _url_sem_senha() -> str:
    """A URL do banco com a senha ocultada, para log.

    Um script de operação imprime a URL para que se saiba em qual banco
    ele mexeu. Imprimi-la inteira colocaria a senha no terminal, no
    histórico do shell e no log de CI.
    """
    url = settings.database_url
    if "@" not in url:
        return url
    credenciais, resto = url.split("@", 1)
    esquema, _, usuario_senha = credenciais.partition("://")
    usuario = usuario_senha.split(":", 1)[0]
    return f"{esquema}://{usuario}:***@{resto}"


async def _verificar_conexao() -> None:
    """Falha cedo e com mensagem clara se o banco não responder."""
    engine = criar_engine()
    try:
        async with engine.connect() as conexao:
            await conexao.execute(text("SELECT 1"))
    finally:
        await engine.dispose()


def _tabelas(sincrona) -> list[str]:
    """Tabelas do schema padrão e, prefixadas, as dos demais schemas.

    Cada um dos outros schemas é criado por uma migração: `rag` pela
    ingestão do executor próprio, `portfolio` pelos dados de projeto e
    `webhook` pelas notificações das fontes externas. Sem listá-los, o
    relatório diria que a migração rodou e não mostraria o que ela criou.
    """
    inspetor = inspect(sincrona)
    existentes = set(inspetor.get_schema_names())
    tabelas = sorted(inspetor.get_table_names())
    for esquema in ESQUEMAS:
        if esquema in existentes:
            tabelas += [
                f"{esquema}.{nome}"
                for nome in sorted(inspetor.get_table_names(schema=esquema))
            ]
    return tabelas


async def _relatar() -> int:
    """Imprime as tabelas e a revisão aplicada. Devolve quantas tabelas há."""
    engine = criar_engine()
    try:
        async with engine.connect() as conexao:
            tabelas = await conexao.run_sync(_tabelas)
            revisao = await conexao.scalar(text("SELECT version_num FROM alembic_version"))
    finally:
        await engine.dispose()

    print(f"Revisão aplicada: {revisao}")
    print(f"Tabelas ({len(tabelas)}): {', '.join(tabelas)}")
    return len(tabelas)


def main() -> int:
    analisador = argparse.ArgumentParser(description=__doc__)
    analisador.add_argument(
        "--versao",
        default="head",
        help="Revisão alvo do Alembic (padrão: head).",
    )
    analisador.add_argument(
        "--conferir",
        action="store_true",
        help="Só relata o estado atual, sem aplicar migração.",
    )
    argumentos = analisador.parse_args()

    print(f"Banco: {_url_sem_senha()}")

    try:
        asyncio.run(_verificar_conexao())
    except Exception as erro:  # noqa: BLE001 — a causa vai na mensagem
        print(
            f"Não foi possível conectar ao banco: {erro}\n"
            "Verifique se o serviço está no ar "
            "(docker compose -f infra/docker-compose.yml up -d db) e se "
            "DATABASE_URL aponta para ele.",
            file=sys.stderr,
        )
        return 1

    if not argumentos.conferir:
        configuracao = Config(str(ALEMBIC_INI))
        configuracao.set_main_option("script_location", str(RAIZ / "migrations"))
        command.upgrade(configuracao, argumentos.versao)

    asyncio.run(_relatar())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
