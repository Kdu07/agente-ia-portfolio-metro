"""Endpoint principal de conversação.

Recebe a mensagem do usuário, delega ao orquestrador do pipeline e
devolve a resposta. Esta rota não contém lógica de PLN: apenas conecta
HTTP ao pipeline.
"""

from fastapi import APIRouter, Depends

from app.api.deps import UsuarioAutenticado, obter_usuario_atual
from app.pipeline.orchestrator import Orchestrator
from app.schemas.chat import ChatRequest, ChatResponse

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def enviar_mensagem(
    request: ChatRequest,
    usuario: UsuarioAutenticado = Depends(obter_usuario_atual),
) -> ChatResponse:
    """Processa uma mensagem do usuário através do pipeline de PLN.

    Fluxo: injection -> PII -> intenção -> Copilot -> resposta.
    Mensagens bloqueadas retornam uma resposta explicativa, nunca erro 500.
    """
    orchestrator = Orchestrator()
    return await orchestrator.processar(request, usuario)
