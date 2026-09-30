"""Carga HTTP para os cenários TNF-DES-01, 03, 04 e 07.

O ambiente de teste fornece a sessão e o executor dublado. Nenhuma
credencial ou resposta de serviço externo fica registrada no repositório.
"""

from __future__ import annotations

import json
import os

from locust import HttpUser, between, task


def _cabecalhos() -> dict[str, str]:
    token = os.getenv("PERF_BEARER_TOKEN")
    return {"Authorization": f"Bearer {token}"} if token else {}


class ChatUser(HttpUser):
    """Usuário sintético que mantém uma conversa durante a medição."""

    wait_time = between(
        float(os.getenv("PERF_MIN_WAIT_SECONDS", "1")),
        float(os.getenv("PERF_MAX_WAIT_SECONDS", "3")),
    )
    host = os.getenv("PERF_TARGET", "http://localhost:8000")

    def on_start(self) -> None:
        self.conversa_id: str | None = None
        cookie = os.getenv("PERF_SESSION_COOKIE")
        if cookie:
            self.client.cookies.set("sessao", cookie)

    @task
    def enviar_chat(self) -> None:
        corpo = {
            # Frase canônica do catálogo: a carga deve atravessar a
            # classificação e alcançar o executor sintético. O texto
            # anterior, com um código fora do vocabulário de treino,
            # podia cair em baixa confiança e medir apenas uma recusa.
            "mensagem": os.getenv("PERF_MESSAGE", "Qual o status do projeto XPTO?"),
        }
        if self.conversa_id:
            corpo["conversa_id"] = self.conversa_id

        with self.client.post(
            os.getenv("PERF_CHAT_PATH", "/chat"),
            json=corpo,
            headers=_cabecalhos(),
            name="POST /chat",
            catch_response=True,
        ) as resposta:
            if resposta.status_code != 200:
                resposta.failure(f"HTTP {resposta.status_code}")
                return
            try:
                dados = resposta.json()
            except json.JSONDecodeError:
                resposta.failure("resposta não é JSON")
                return
            conversa_id = dados.get("conversa_id")
            if not conversa_id or not dados.get("desfecho"):
                resposta.failure("contrato ChatResponse incompleto")
                return
            # Uma resposta HTTP 200 não basta: bloqueios e recusas também
            # usam 200 por contrato. Falhar a amostra se ela não foi
            # encaminhada impede um falso sucesso de desempenho.
            esperado = os.getenv("PERF_EXPECTED_DESFECHO", "encaminhada")
            if esperado and dados["desfecho"] != esperado:
                resposta.failure(f"desfecho esperado={esperado}, observado={dados['desfecho']}")
                return
            self.conversa_id = conversa_id
