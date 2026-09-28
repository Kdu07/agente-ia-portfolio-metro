"""Montagem do executor fora da camada HTTP.

API, processamento de áudio e worker usam esta mesma fábrica. Isso evita
que os canais interpretem a configuração de formas diferentes e garante
um único ponto de decisão para ``settings.executor`` e para o executor
sintético dos testes de desempenho.
"""

from typing import Any

from app.config import settings
from app.copilot.client import CopilotClient
from app.executor.base import Executor
from app.executor.desempenho import ExecutorDesempenho
from app.schemas.usuario import UsuarioAutenticado

EXECUTORES = ("copilot", "proprio")


def montar_executor(banco: Any, usuario: UsuarioAutenticado) -> Executor:
    """Monta somente o executor; o restante do pipeline não muda em carga."""
    if settings.performance_mode:
        return ExecutorDesempenho()

    escolhido = settings.executor.strip().lower()
    if escolhido == "copilot":
        return CopilotClient()
    if escolhido == "proprio":
        from app.rag.executor import montar_executor as montar_executor_rag

        return montar_executor_rag(banco, usuario)
    raise ValueError(f"executor inválido: {escolhido!r}. Esperado um de {EXECUTORES}")
