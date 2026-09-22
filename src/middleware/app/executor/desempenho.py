"""Executor sintético opt-in para medir o middleware sem o Copilot."""

import asyncio

from app.config import settings
from app.executor.base import RespostaExecutor


class ExecutorDesempenho:
    """Resposta determinística com atraso controlado para TNF-DES."""

    async def enviar(
        self,
        texto: str,
        intencao_id: str,
        exige_confirmacao: bool,
        conversa_externa_id: str | None = None,
        historico=(),
    ) -> RespostaExecutor:
        await asyncio.wait_for(
            asyncio.sleep(settings.performance_executor_delay_ms / 1000),
            timeout=settings.performance_executor_timeout_ms / 1000,
        )
        return RespostaExecutor(
            texto="Resposta sintética do executor de desempenho.",
            conversa_externa_id=conversa_externa_id,
        )