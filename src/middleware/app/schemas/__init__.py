"""Contratos de entrada e saída da API (modelos Pydantic)."""

from app.schemas.audio import AudioUploadResponse, TranscricaoResponse
from app.schemas.chat import ChatRequest, ChatResponse
from app.schemas.conversa import ConversaResponse
from app.schemas.intencao import IntencaoResponse
from app.schemas.rotina import RotinaResponse
from app.schemas.usuario import UsuarioResponse

__all__ = [
    "AudioUploadResponse",
    "TranscricaoResponse",
    "ChatRequest",
    "ChatResponse",
    "ConversaResponse",
    "IntencaoResponse",
    "RotinaResponse",
    "UsuarioResponse",
]
