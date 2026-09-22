import base64
import hmac
from dataclasses import replace

import pytest

from app.auth.webhooks import ChavePortfolio, WebhookRecusado, verificar_portfolio

CHAVE = ChavePortfolio(bytes(range(32)), 1000, 3000)
CORPO = b'{"source_id":"portfolio"}'


def cabecalhos(timestamp="2000"):
    assinatura = hmac.digest(
        CHAVE.segredo, f"portfolio\nk1\n{timestamp}\n".encode() + CORPO, "sha256"
    )
    return [
        (b"X-Prata-Source", b"portfolio"),
        (b"X-Prata-Key-Id", b"k1"),
        (b"X-Prata-Timestamp", timestamp.encode()),
        (b"X-Prata-Signature", base64.b64encode(assinatura)),
    ]


def verificar(headers=None, corpo=CORPO, chave=CHAVE, agora=2000):
    return verificar_portfolio(
        cabecalhos() if headers is None else headers,
        corpo, {("portfolio", "k1"): chave}, agora=agora,
    )


@pytest.mark.parametrize("agora", [1700, 2000, 2300])
def test_assinatura_valida_e_limites_da_janela(agora):
    assert verificar(agora=agora) == "portfolio"


@pytest.mark.parametrize("agora", [1699, 2301])
def test_recusa_fora_da_janela(agora):
    with pytest.raises(WebhookRecusado) as erro:
        verificar(agora=agora)
    assert erro.value.status == 401


def test_nao_normaliza_corpo():
    with pytest.raises(WebhookRecusado):
        verificar(corpo=b'{ "source_id": "portfolio" }')


@pytest.mark.parametrize("chave", [
    replace(CHAVE, revogada=True),
    replace(CHAVE, valida_ate=2000),
    replace(CHAVE, valida_desde=2001),
    replace(CHAVE, segredo=b"x" * 32),
])
def test_recusa_chave_invalida(chave):
    with pytest.raises(WebhookRecusado) as erro:
        verificar(chave=chave)
    assert erro.value.status == 401


@pytest.mark.parametrize("indice", range(4))
def test_recusa_cabecalho_ausente_ou_repetido(indice):
    headers = cabecalhos()
    with pytest.raises(WebhookRecusado) as erro:
        verificar(headers[:indice] + headers[indice + 1:])
    assert erro.value.status == 401
    with pytest.raises(WebhookRecusado) as erro:
        verificar(headers + [(headers[indice][0].lower(), headers[indice][1])])
    assert erro.value.status == 400


@pytest.mark.parametrize("valor", ["02000", "+2000", "2000.0", " 2000"])
def test_timestamp_deve_ser_canonico(valor):
    with pytest.raises(WebhookRecusado) as erro:
        verificar(cabecalhos(valor))
    assert erro.value.status == 400


@pytest.mark.parametrize("assinatura", [b"!", b"", base64.b64encode(b"curta")])
def test_recusa_assinatura_malformada(assinatura):
    headers = cabecalhos()
    headers[-1] = (headers[-1][0], assinatura)
    with pytest.raises(WebhookRecusado) as erro:
        verificar(headers)
    assert erro.value.status == 401


def test_segredo_nao_aparece_na_representacao():
    assert "segredo=" not in repr(CHAVE)


def test_timestamp_enorme_e_recusado_sem_overflow():
    with pytest.raises(WebhookRecusado) as erro:
        verificar(cabecalhos("9" * 2000), agora=2000.0)
    assert erro.value.status == 401
