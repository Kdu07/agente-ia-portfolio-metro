"""Endpoint principal de conversação.

Recebe a mensagem do usuário, delega ao orquestrador do pipeline e
devolve a resposta. Esta rota não contém lógica de PLN: apenas conecta
HTTP ao pipeline.
"""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import UsuarioAtual, obter_orquestrador
from app.pipeline.orquestrador import Orquestrador
from app.schemas.chat import ChatRequest, ChatResponse

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def enviar_mensagem(
    request: ChatRequest,
    usuario: UsuarioAtual,
    orquestrador: Annotated[Orquestrador, Depends(obter_orquestrador)],
) -> ChatResponse:
    """Processa uma mensagem do usuário através do pipeline.

    Fluxo: injeção -> abuso -> intenção -> Copilot -> saída -> registro.
    Mensagens bloqueadas retornam 200 com resposta explicativa e
    `bloqueada=True`, nunca erro 500: um bloqueio é decisão do pipeline,
    não falha do servidor, e tratá-lo como erro faria o cliente exibir
    "algo deu errado" no lugar da orientação.
    """
    return await orquestrador.processar(request, usuario, canal=request.canal)
