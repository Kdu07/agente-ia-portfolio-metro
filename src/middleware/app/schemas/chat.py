"""Contratos do endpoint /chat."""

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Mensagem enviada pelo usuário ao agente."""

    mensagem: str = Field(min_length=1, max_length=4000)
    conversa_id: str | None = None  # continuação de uma conversa existente


class ChatResponse(BaseModel):
    """Resposta do agente ao usuário."""

    resposta: str
    conversa_id: str
    intencao_id: str | None = None  # intenção classificada (transparência)
    bloqueada: bool = False  # True quando o pipeline recusou a mensagem
