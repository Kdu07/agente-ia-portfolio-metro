"""Contrato HTTP da rota `POST /webhooks/google-drive` (Projeto.md 9.1.2.7.1).

A lógica de recebimento é dublada: aqui se verifica só o que a rota
promete ao Google — status, corpo vazio no sucesso, envelope de erro com
mensagem genérica, `Retry-After` no 503 e o limite de leitura do corpo.
A lógica tem seus próprios testes em test_webhook_drive_recebimento.py.
"""

import pytest
from fastapi.testclient import TestClient

from app.api import deps
from app.api.routes import webhooks
from app.auth.webhooks import WebhookRecusado
from app.main import app

URL = "/webhooks/google-drive"


@pytest.fixture
def cliente(monkeypatch):
    chamadas: list[dict] = []
    resultado: dict = {"status": 202, "erro": None}

    async def receber(cabecalhos, corpo, **opcoes):
        chamadas.append({"cabecalhos": list(cabecalhos), "corpo": corpo, **opcoes})
        if resultado["erro"] is not None:
            raise resultado["erro"]
        return resultado["status"]

    monkeypatch.setattr(webhooks, "receber_notificacao", receber)
    monkeypatch.setitem(app.dependency_overrides, deps.obter_produtor, lambda: "produtor")
    monkeypatch.setitem(app.dependency_overrides, deps.obter_fabrica_sessoes, lambda: "fabrica")
    with TestClient(app) as c:
        yield c, chamadas, resultado


@pytest.mark.parametrize("status", [202, 204])
def test_sucesso_responde_sem_corpo(cliente, status):
    c, _, resultado = cliente
    resultado["status"] = status

    resposta = c.post(URL, headers={"X-Goog-Resource-State": "change"})

    assert resposta.status_code == status
    assert resposta.content == b""


def test_repassa_cabecalhos_brutos_corpo_e_dependencias(cliente):
    c, chamadas, _ = cliente

    c.post(URL, headers={"X-Goog-Channel-ID": "canal-1"})

    [chamada] = chamadas
    assert (b"x-goog-channel-id", b"canal-1") in chamada["cabecalhos"]
    assert chamada["corpo"] == b""
    assert (chamada["produtor"], chamada["fabrica"]) == ("produtor", "fabrica")


@pytest.mark.parametrize(
    "status,codigo",
    [
        (400, "WEBHOOK_INVALIDO"),
        (401, "WEBHOOK_NAO_AUTORIZADO"),
        (413, "WEBHOOK_INVALIDO"),
        (431, "WEBHOOK_INVALIDO"),
    ],
)
def test_recusa_usa_envelope_com_mensagem_generica(cliente, status, codigo):
    c, _, resultado = cliente
    resultado["erro"] = WebhookRecusado(status, codigo)

    resposta = c.post(URL)

    assert resposta.status_code == status
    detalhe = resposta.json()["detail"]
    assert detalhe["codigo"] == codigo
    assert detalhe["mensagem"] == webhooks.MENSAGENS[codigo]
    assert "retry-after" not in resposta.headers


def test_indisponibilidade_pede_nova_tentativa_em_5_segundos(cliente):
    c, _, resultado = cliente
    resultado["erro"] = WebhookRecusado(503, "WEBHOOK_INDISPONIVEL")

    resposta = c.post(URL)

    assert resposta.status_code == 503
    assert resposta.headers["retry-after"] == "5"
    assert resposta.json()["detail"]["codigo"] == "WEBHOOK_INDISPONIVEL"


def test_falha_inesperada_nao_vaza_detalhes(cliente):
    c, _, resultado = cliente
    resultado["erro"] = RuntimeError("segredo-interno do banco")

    resposta = c.post(URL)

    assert resposta.status_code == 500
    assert resposta.json()["detail"]["codigo"] == "WEBHOOK_ERRO_INTERNO"
    assert "segredo-interno" not in resposta.text


def test_corpo_acima_do_limite_e_recusado_sem_processar(cliente):
    c, chamadas, _ = cliente

    resposta = c.post(URL, content=b"x" * (webhooks.LIMITE_CORPO_DRIVE + 1))

    assert resposta.status_code == 413
    assert resposta.json()["detail"]["codigo"] == "WEBHOOK_INVALIDO"
    assert chamadas == []


def test_corpo_dentro_do_limite_segue_para_a_validacao(cliente):
    c, chamadas, _ = cliente

    c.post(URL, content=b"{}")

    assert chamadas[0]["corpo"] == b"{}"


def test_metodo_diferente_de_post_responde_405_com_allow(cliente):
    c, chamadas, _ = cliente

    resposta = c.get(URL)

    assert resposta.status_code == 405
    assert resposta.headers["allow"] == "POST"
    assert chamadas == []
