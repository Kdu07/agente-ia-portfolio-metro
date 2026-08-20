"""Entrypoint da API do middleware de PLN.

Sobe a aplicação FastAPI e registra as rotas. Nenhuma lógica de negócio
vive aqui: este arquivo só monta a aplicação.

Execução local:
    uvicorn app.main:app --reload
"""

from fastapi import FastAPI

from app.api.routes import chat, health

app = FastAPI(
    title="Middleware PLN - Portfólio Metrô SP",
    description=(
        "Camada de PLN entre o usuário e o Copilot Studio: "
        "classifica intenções, mascara dados sensíveis e "
        "bloqueia tentativas de prompt injection."
    ),
    version="0.1.0",
)

app.include_router(health.router, tags=["infra"])
app.include_router(chat.router, tags=["chat"])
