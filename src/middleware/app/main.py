"""Entrypoint da API do middleware.

Sobe a aplicação FastAPI e registra as rotas. Nenhuma lógica de negócio
vive aqui: este arquivo só monta a aplicação.

O agendador de rotinas NÃO sobe aqui — ele roda no contêiner `worker`
(app/worker.py). Embutir o agendador na API faria duas réplicas
dispararem a mesma rotina duas vezes.

Execução local:
    uvicorn app.main:app --reload
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import auth, chat, conversas, health, intencoes, portfolio, rotinas, voz
from app.persistence import sessao as db


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Cria o pool de conexões na subida e o fecha no encerramento.

    O engine vive pelo processo inteiro. Criá-lo por requisição
    descartaria o pool e transformaria cada mensagem num handshake novo
    com o PostgreSQL.
    """
    db.iniciar()
    yield
    await db.encerrar()


app = FastAPI(
    lifespan=lifespan,
    title="Middleware — Agente de Portfólio Metrô SP",
    description=(
        "Camada entre a interface web e o Copilot Studio: bloqueia prompt "
        "injection e prompts maliciosos, classifica e registra intenções, "
        "analisa esses dados e executa rotinas agendadas."
    ),
    version="0.2.0",
)

app.include_router(health.router, tags=["infra"])
app.include_router(auth.router, tags=["auth"])
app.include_router(chat.router, tags=["chat"])
app.include_router(conversas.router, tags=["conversas"])
app.include_router(voz.router, tags=["voz"])
# Rotas restritas: a permissão é exigida no próprio router (ver cada módulo).
app.include_router(intencoes.router, tags=["intencoes"])
app.include_router(rotinas.router, tags=["rotinas"])
app.include_router(portfolio.router, tags=["portfolio"])
