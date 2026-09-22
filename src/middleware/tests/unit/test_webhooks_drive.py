import hashlib
from dataclasses import replace

import pytest

from app.auth.webhooks import WebhookRecusado
from app.auth.webhooks_drive import CanalDrive, verificar_drive

ID = "546d4256-6804-41bc-887a-238ac5cce921"
TOKEN = "a" * 64
CANAL = CanalDrive(
    "corpus", hashlib.sha256(TOKEN.encode()).digest(), 3000,
    "recurso", "https://www.googleapis.com/drive/v3/changes", pendente=False,
)


def headers(**alteracoes):
    valores = {
        "channel-id": ID, "channel-token": TOKEN, "resource-id": "recurso",
        "resource-uri": CANAL.recurso_uri, "resource-state": "change", "message-number": "2",
    }
    valores.update(alteracoes)
    return [(f"X-Goog-{k}".encode(), v.encode()) for k, v in valores.items()]


def verificar(cabecalhos=None, canal=CANAL, corpo=b"", **kwargs):
    return verificar_drive(
        headers() if cabecalhos is None else cabecalhos, corpo, {ID: canal},
        fonte="corpus", agora=2000, **kwargs,
    )


@pytest.mark.parametrize("estado,processar", [
    ("sync", False), ("change", True), ("changed", True), ("future", False),
])
def test_estado_autenticado(estado, processar):
    evento = verificar(headers(**{"resource-state": estado}))
    assert evento.processar is processar
    assert evento.fonte == "corpus"


def test_numero_grande_sem_perda_e_zeros_normalizados():
    numero = "9" * 64
    assert verificar(headers(**{"message-number": numero})).numero == numero
    assert verificar(headers(**{"message-number": "0002"})).numero == "2"


@pytest.mark.parametrize("campo,valor,status", [
    ("channel-token", "incorreto", 401), ("channel-token", "", 401),
    ("channel-token", "a" * 257, 400),
    ("resource-id", "outro", 401), ("resource-uri", "https://example.org", 401),
    ("channel-id", "invalido", 400),
    ("channel-id", "546d4256-6804-41bc-887a-238ac5cce922", 401),
    ("message-number", "0", 400), ("message-number", "-1", 400),
    ("message-number", "9" * 65, 400), ("resource-state", "bad state", 400),
])
def test_recusa_campos_invalidos(campo, valor, status):
    with pytest.raises(WebhookRecusado) as erro:
        verificar(headers(**{campo: valor}))
    assert erro.value.status == status


@pytest.mark.parametrize("canal", [
    replace(CANAL, revogado=True), replace(CANAL, expira_em=2000),
    replace(CANAL, fonte="outro"),
])
def test_recusa_cadastro_invalido(canal):
    with pytest.raises(WebhookRecusado) as erro:
        verificar(canal=canal)
    assert erro.value.status == 401


def test_sync_pendente_nao_vincula_recurso_nem_publica():
    canal = replace(CANAL, pendente=True, recurso_id=None, recurso_uri=None)
    evento = verificar(headers(**{"resource-state": "sync"}), canal=canal)
    assert not evento.processar
    assert canal.recurso_id is None
    with pytest.raises(WebhookRecusado) as erro:
        verificar(canal=canal)
    assert erro.value.status == 503


@pytest.mark.parametrize("indice", range(6))
def test_rejeita_headers_ausentes_e_repetidos(indice):
    valores = headers()
    with pytest.raises(WebhookRecusado) as erro:
        verificar(valores[:indice] + valores[indice + 1:])
    assert erro.value.status == (401 if indice == 1 else 400)
    with pytest.raises(WebhookRecusado) as erro:
        verificar(valores + [(valores[indice][0].lower(), valores[indice][1])])
    assert erro.value.status == 400


@pytest.mark.parametrize("corpo,status", [(b"{}", 400), (b"x" * 1025, 413)])
def test_rejeita_corpo(corpo, status):
    with pytest.raises(WebhookRecusado) as erro:
        verificar(corpo=corpo)
    assert erro.value.status == status


def test_expiracao_do_cabecalho_nao_estende_cadastro():
    with pytest.raises(WebhookRecusado) as erro:
        verificar(headers(**{"channel-expiration": "future"}),
                  canal=replace(CANAL, expira_em=1999))
    assert erro.value.status == 401
