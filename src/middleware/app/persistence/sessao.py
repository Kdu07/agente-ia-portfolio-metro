"""Engine e sessão do SQLAlchemy.

Ponto único de criação do engine assíncrono. Fica separado de
repository.py para que os repositórios recebam a sessão pronta e possam
ser testados contra um banco real sem que nada mais no processo saiba
disso.

O engine é criado uma vez por processo, não por requisição: recriá-lo a
cada chamada descartaria o pool de conexões e transformaria cada
mensagem num handshake novo com o PostgreSQL. Quem o cria é o `lifespan`
da aplicação (app/main.py); o `worker` do agendador tem o próprio ciclo.
"""

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import settings

# Preenchidos por `iniciar` e zerados por `encerrar`. Módulo-nível porque
# a dependência do FastAPI precisa alcançá-los sem receber a aplicação.
_engine: AsyncEngine | None = None
_fabrica: async_sessionmaker[AsyncSession] | None = None


def criar_engine() -> AsyncEngine:
    """Instancia o engine assíncrono a partir de settings.database_url.

    `pool_pre_ping` testa a conexão antes de entregá-la. Não é zelo
    excessivo: o `worker` fica ocioso entre disparos, e o PostgreSQL
    derruba conexões paradas — sem o ping, a primeira rotina depois de
    um intervalo longo falharia com a conexão morta que o pool guardou.
    """
    return create_async_engine(settings.database_url, pool_pre_ping=True)


def iniciar() -> None:
    """Cria engine e fábrica de sessões. Chamado uma vez, na subida."""
    global _engine, _fabrica
    if _engine is not None:
        return
    _engine = criar_engine()
    # `expire_on_commit=False` porque, com o padrão, ler qualquer atributo
    # depois do commit dispara uma consulta nova — e no encerramento da
    # requisição a sessão já foi fechada. Os repositórios devolvem
    # dataclasses de domínio, então não há estado a reconciliar.
    _fabrica = async_sessionmaker(_engine, expire_on_commit=False)


async def encerrar() -> None:
    """Fecha o pool de conexões. Chamado no encerramento do processo."""
    global _engine, _fabrica
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _fabrica = None


def fabrica_de_sessoes() -> async_sessionmaker[AsyncSession]:
    """Devolve a fábrica, criando-a se ainda não existir.

    A criação sob demanda serve ao `worker` e aos scripts, que não passam
    pelo lifespan do FastAPI mas precisam do mesmo engine.
    """
    if _fabrica is None:
        iniciar()
    assert _fabrica is not None
    return _fabrica


async def obter_sessao() -> AsyncIterator[AsyncSession]:
    """Cede uma sessão por requisição, com commit/rollback no encerramento.

    Usado como dependência do FastAPI. O commit acontece aqui, e não nos
    repositórios: assim uma requisição que escreve em mais de uma tabela
    — o upsert do usuário junto com a interação, por exemplo — é uma
    transação só, e um erro no meio não deixa metade gravada.

    O `worker` do agendador não passa por aqui: ele abre a própria sessão
    por execução de rotina, porque não há requisição HTTP delimitando o
    escopo.
    """
    async with fabrica_de_sessoes()() as sessao:
        try:
            yield sessao
            await sessao.commit()
        except Exception:
            await sessao.rollback()
            raise
