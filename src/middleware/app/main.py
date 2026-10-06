"""Entrypoint da API do middleware.

Sobe a aplicação FastAPI e registra as rotas. Nenhuma lógica de negócio
vive aqui: este arquivo só monta a aplicação.

O agendador de rotinas NÃO sobe aqui — ele roda no contêiner `worker`
(app/worker.py). Embutir o agendador na API faria duas réplicas
dispararem a mesma rotina duas vezes.

Execução local:
    uvicorn app.main:app --reload
"""

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import TimeoutError as SQLAlchemyTimeoutError

from app.api.routes import (
    auth,
    avisos,
    chat,
    conversas,
    health,
    intencoes,
    portfolio,
    rotinas,
    voz,
    webhooks,
)
from app.config import settings
from app.mensageria.produtor import ProdutorEventos
from app.persistence import sessao as db
from app.pipeline.guardas import content_safety
from app.pipeline.intencao import classificador

FORMATO_LOG = "%(levelname)s:     %(name)s: %(message)s"


def configurar_logs(nome: str = "app") -> None:
    """Liga o nível INFO dos loggers do middleware, com saída no stderr.

    O uvicorn configura só os loggers dele. Sem isto, os do pacote `app`
    ficam sem handler, e o Python só imprime WARNING para cima: a linha
    `RAG situacao=... recuperados=...` de `rag/fluxo.py`, que diz se uma
    abstenção veio da busca ou do modelo, não chegava ao Log Analytics.
    Nenhum INFO do pacote carrega texto de pergunta, resposta ou corpus,
    só identificadores, contagens e scores.

    O handler fica no logger `app`, e não na raiz, para não duplicar as
    linhas do uvicorn nem ligar o INFO de bibliotecas. Idempotente:
    `--reload` e os testes importam este módulo mais de uma vez.
    """
    logger = logging.getLogger(nome)
    if not logger.handlers:
        manipulador = logging.StreamHandler()
        manipulador.setFormatter(logging.Formatter(FORMATO_LOG))
        logger.addHandler(manipulador)
    logger.setLevel(logging.INFO)


configurar_logs()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Cria o pool de conexões e o produtor de eventos na subida e os fecha no encerramento.

    O engine vive pelo processo inteiro. Criá-lo por requisição
    descartaria o pool e transformaria cada mensagem num handshake novo
    com o PostgreSQL.

    Com `aquecer_modelos`, o classificador carrega numa thread enquanto a
    API já responde: `/health` fica verde na hora e `/health/pronto` só
    depois da carga. Esperar aqui, antes do `yield`, deixaria a porta
    fechada por minutos, e a sonda de início reiniciaria a réplica.

    O produtor só conecta ao RabbitMQ na primeira publicação: a API sobe
    com o broker fora do ar, e só as rotas que publicam respondem erro
    transitório até ele voltar.
    """
    db.iniciar()
    await content_safety.iniciar()
    app.state.produtor_eventos = ProdutorEventos.a_partir_de(settings)
    app.state.aquecimento = (
        asyncio.create_task(asyncio.to_thread(classificador.aquecer))
        if settings.aquecer_modelos
        else None
    )
    yield
    await app.state.produtor_eventos.encerrar()
    await content_safety.encerrar()
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


async def tratar_pool_esgotado(request: Request, erro: SQLAlchemyTimeoutError) -> JSONResponse:
    """Transforma saturação do pool em indisponibilidade temporária controlada.

    A causa detalhada fica somente no log; a resposta não expõe DSN, tamanho
    do pool nem mensagem interna do driver. O cliente recebe um erro transitório
    e pode repetir a solicitação depois do intervalo indicado.
    """
    logging.getLogger(__name__).warning(
        "Pool de banco esgotado em %s %s: %s",
        request.method,
        request.url.path,
        type(erro).__name__,
    )
    return JSONResponse(
        status_code=503,
        content={"detail": "Serviço temporariamente ocupado. Tente novamente em instantes."},
        headers={"Retry-After": "2"},
    )


app.add_exception_handler(voz.ErroAudioApi, voz.tratar_erro_audio)
app.add_exception_handler(SQLAlchemyTimeoutError, tratar_pool_esgotado)

app.include_router(health.router, tags=["infra"])
app.include_router(auth.router, tags=["auth"])
app.include_router(chat.router, tags=["chat"])
app.include_router(conversas.router, tags=["conversas"])
app.include_router(voz.router, tags=["voz"])
# Rotas restritas: a permissão é exigida no próprio router (ver cada módulo).
app.include_router(intencoes.router, tags=["intencoes"])
app.include_router(rotinas.router, tags=["rotinas"])
app.include_router(portfolio.router, tags=["portfolio"])
app.include_router(avisos.router, tags=["avisos"])
# Sem sessão de usuário: autenticidade do emissor (app/auth/webhooks*.py).
app.include_router(webhooks.router, tags=["webhooks"])
