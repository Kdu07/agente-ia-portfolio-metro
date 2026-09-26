"""Montagem do executor fora da camada HTTP.

API e worker usam esta mesma fábrica. Isso evita que a execução agendada
importe dependências do FastAPI e garante que ``settings.executor`` tenha um
único ponto de decisão.
"""

from typing import Any

from app.config import settings
from app.copilot.client import CopilotClient
from app.executor.base import Executor
from app.schemas.usuario import UsuarioAutenticado

EXECUTORES = ("copilot", "proprio")


def montar_executor(banco: Any, usuario: UsuarioAutenticado) -> Executor:
    """Monta o adaptador configurado no escopo atual do usuário."""
    escolhido = settings.executor.strip().lower()
    if escolhido == "copilot":
        return CopilotClient()
    if escolhido == "proprio":
        from app.rag.executor import montar_executor as montar_executor_rag

        return montar_executor_rag(banco, usuario)
    raise ValueError(f"executor inválido: {escolhido!r}. Esperado um de {EXECUTORES}")
