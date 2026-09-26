"""Contratos do endpoint /chat."""

from pydantic import BaseModel, Field

from app.persistence.models import Canal


class ChatRequest(BaseModel):
    """Mensagem enviada pelo usuário ao agente."""

    mensagem: str = Field(min_length=1, max_length=4000)
    conversa_id: str | None = None  # continuação de uma conversa existente
    # Informado pelo cliente para distinguir texto digitado de ditado. Não
    # é dado de segurança — um cliente mentiroso mudaria só o rótulo do
    # registro, e as guardas valem igualmente para os dois. `Canal.ROTINA`
    # nunca vem daqui: o agendador passa o canal direto ao orquestrador.
    canal: Canal = Canal.CHAT


class ChatResponse(BaseModel):
    """Resposta do agente ao usuário.

    `conversa_id` é sempre o identificador do middleware, nunca o
    conversationId do Direct Line: o cliente não deve conhecer o executor.
    """

    resposta: str
    conversa_id: str
    intencao_id: str | None = None  # intenção classificada (transparência)
    desfecho: str  # valor de pipeline.desfechos.Desfecho
    bloqueada: bool = False  # True quando o pipeline não entregou a resposta
    # Uso interno da execução de rotinas: permite ligar o disparo à linha
    # que o pipeline gravou sem ampliar o contrato público de /chat.
    interacao_id: str | None = Field(default=None, exclude=True)
    execucao_id: str | None = Field(default=None, exclude=True)
