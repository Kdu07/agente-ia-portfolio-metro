"""Engine e sessão do SQLAlchemy.

Ponto único de criação do engine assíncrono. Fica separado de
repository.py para que os repositórios recebam a sessão pronta e possam
ser testados contra um banco em memória — ou dublados por completo, como
fazem os testes de integração hoje.

O engine é criado uma vez por processo, não por requisição: recriá-lo a
cada chamada descartaria o pool de conexões e transformaria cada
mensagem num handshake novo com o PostgreSQL.

TODO (onda 1): implementar com create_async_engine / async_sessionmaker
sobre settings.database_url, e ligar o ciclo de vida ao lifespan da
aplicação em main.py.
"""

from collections.abc import AsyncIterator
from typing import Any


def criar_engine() -> Any:
    """Instancia o engine assíncrono a partir de settings.database_url."""
    raise NotImplementedError("Engine a implementar na onda 1")


async def obter_sessao() -> AsyncIterator[Any]:
    """Cede uma sessão por requisição, com commit/rollback no encerramento.

    Usado como dependência do FastAPI. O `worker` do agendador não passa
    por aqui: ele abre a própria sessão por execução de rotina, porque
    não há requisição HTTP delimitando o escopo.
    """
    raise NotImplementedError("Sessão a implementar na onda 1")
