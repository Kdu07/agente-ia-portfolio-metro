"""Contratos das rotas de histórico de conversas."""

from datetime import datetime

from pydantic import BaseModel

from app.persistence.models import Canal


class ConversaResumo(BaseModel):
    """Item da lista de histórico.

    Não traz os turnos: a lista carrega dezenas de conversas e não deve
    puxar o conteúdo de todas para renderizar a barra lateral.
    """

    id: str
    titulo: str | None
    criada_em: datetime
    atualizada_em: datetime
    total_turnos: int


class TurnoResposta(BaseModel):
    """Um turno de conversa, como o histórico o exibe.

    Traz `desfecho` e `intencao_id` de propósito: quando o usuário reabre
    uma conversa antiga e vê uma recusa, é útil saber que foi recusa e
    não resposta. É a mesma transparência que o /chat oferece ao vivo.
    """

    id: str
    prompt: str
    resposta: str
    canal: Canal
    intencao_id: str | None
    desfecho: str
    bloqueada: bool
    criada_em: datetime


class ConversaDetalhe(BaseModel):
    """Uma conversa com seus turnos, para retomada."""

    id: str
    titulo: str | None
    criada_em: datetime
    turnos: list[TurnoResposta]
