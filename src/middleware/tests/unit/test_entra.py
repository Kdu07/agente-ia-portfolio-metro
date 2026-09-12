"""Testes do cliente do Entra ID, sem tenant nenhum.

O endpoint de token é dublado com o `MockTransport` do httpx e o id_token
é assinado por uma chave RSA gerada aqui. A validação que roda é a de
verdade — PyJWT conferindo assinatura, emissor, audiência e expiração —
e o que muda em relação à produção é só de onde vem a chave pública.
"""

import base64
import hashlib
import time
from urllib.parse import parse_qs, urlparse

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from app.auth import entra
from app.config import settings

TENANT = "11111111-2222-3333-4444-555555555555"
CLIENTE = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
EMISSOR = f"https://login.microsoftonline.com/{TENANT}/v2.0"

CHAVE = rsa.generate_private_key(public_exponent=65537, key_size=2048)
OUTRA_CHAVE = rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture(autouse=True)
def tenant_de_teste(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "entra_tenant_id", TENANT)
    monkeypatch.setattr(settings, "entra_client_id", CLIENTE)
    monkeypatch.setattr(settings, "entra_client_secret", "segredo")
    monkeypatch.setattr(settings, "entra_redirect_uri", "http://localhost:5173/api/auth/callback")
    monkeypatch.setattr(entra, "_chave_de_assinatura", lambda token: CHAVE.public_key())


def _fluxo(nonce: str = "nonce-1") -> entra.FluxoPendente:
    return entra.FluxoPendente(estado="estado-1", code_verifier="v" * 64, nonce=nonce)


def _id_token(chave=CHAVE, **sobrescritas) -> str:
    agora = int(time.time())
    claims = {
        "iss": EMISSOR,
        "aud": CLIENTE,
        "iat": agora,
        "nbf": agora,
        "exp": agora + 3600,
        "oid": "oid-fernanda",
        "tid": TENANT,
        "name": "Fernanda Medina",
        "preferred_username": "fernanda@metro.example",
        "nonce": "nonce-1",
        "groups": ["g-lider", "g-intencoes"],
    }
    claims.update(sobrescritas)
    claims = {k: v for k, v in claims.items() if v is not None}
    return jwt.encode(claims, chave, algorithm="RS256", headers={"kid": "k1"})


def _cliente_token(resposta: httpx.Response, recebidos: list | None = None) -> httpx.AsyncClient:
    def tratar(pedido: httpx.Request) -> httpx.Response:
        if recebidos is not None:
            recebidos.append(pedido)
        return resposta

    return httpx.AsyncClient(transport=httpx.MockTransport(tratar))


# --- iniciar_autorizacao -------------------------------------------------


def test_url_de_autorizacao_carrega_pkce_s256_e_o_estado() -> None:
    desafio = entra.iniciar_autorizacao()
    url = urlparse(desafio.url_autorizacao)
    parametros = {k: v[0] for k, v in parse_qs(url.query).items()}

    assert url.netloc == "login.microsoftonline.com"
    assert url.path == f"/{TENANT}/oauth2/v2.0/authorize"
    assert parametros["client_id"] == CLIENTE
    assert parametros["response_type"] == "code"
    assert parametros["state"] == desafio.fluxo.estado
    assert parametros["nonce"] == desafio.fluxo.nonce
    assert parametros["code_challenge_method"] == "S256"
    esperado = (
        base64.urlsafe_b64encode(hashlib.sha256(desafio.fluxo.code_verifier.encode()).digest())
        .rstrip(b"=")
        .decode()
    )
    assert parametros["code_challenge"] == esperado
    # O verifier nunca vai na URL: é ele que prova a posse do código.
    assert desafio.fluxo.code_verifier not in desafio.url_autorizacao


def test_cada_login_gera_estado_verifier_e_nonce_novos() -> None:
    a, b = entra.iniciar_autorizacao().fluxo, entra.iniciar_autorizacao().fluxo
    assert a.estado != b.estado
    assert a.code_verifier != b.code_verifier
    assert a.nonce != b.nonce


def test_sem_configuracao_o_login_e_recusado(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "entra_client_secret", "")
    with pytest.raises(entra.ConfiguracaoAusente, match="entra_client_secret"):
        entra.iniciar_autorizacao()


# --- trocar_codigo -------------------------------------------------------


async def test_troca_valida_devolve_a_identidade() -> None:
    recebidos: list[httpx.Request] = []
    http = _cliente_token(httpx.Response(200, json={"id_token": _id_token()}), recebidos)

    identidade = await entra.trocar_codigo("codigo", _fluxo(), http=http)

    assert identidade == entra.IdentidadeEntra(
        oid="oid-fernanda",
        nome="Fernanda Medina",
        email="fernanda@metro.example",
        grupos=("g-lider", "g-intencoes"),
    )
    corpo = parse_qs(recebidos[0].content.decode())
    assert corpo["code_verifier"] == ["v" * 64]
    assert corpo["grant_type"] == ["authorization_code"]
    assert recebidos[0].url.path == f"/{TENANT}/oauth2/v2.0/token"


async def test_claim_email_tem_precedencia_sobre_o_upn() -> None:
    token = _id_token(email="fernanda.medina@metro.example")
    http = _cliente_token(httpx.Response(200, json={"id_token": token}))
    identidade = await entra.trocar_codigo("codigo", _fluxo(), http=http)
    assert identidade.email == "fernanda.medina@metro.example"


@pytest.mark.parametrize(
    ("descricao", "token"),
    [
        ("assinado por outra chave", lambda: _id_token(chave=OUTRA_CHAVE)),
        ("audiência de outro app", lambda: _id_token(aud="outro-app")),
        (
            "emitido por outro tenant",
            lambda: _id_token(iss="https://login.microsoftonline.com/x/v2.0"),
        ),
        ("expirado", lambda: _id_token(exp=int(time.time()) - 3600)),
        ("nonce de outro fluxo", lambda: _id_token(nonce="nonce-alheio")),
        ("sem nonce", lambda: _id_token(nonce=None)),
        ("sem oid", lambda: _id_token(oid=None)),
    ],
)
async def test_token_que_nao_confere_e_recusado(descricao: str, token) -> None:
    http = _cliente_token(httpx.Response(200, json={"id_token": token()}))
    with pytest.raises(entra.FalhaAutenticacao):
        await entra.trocar_codigo("codigo", _fluxo(), http=http)


async def test_recusa_do_endpoint_de_token_vira_falha() -> None:
    http = _cliente_token(
        httpx.Response(400, json={"error": "invalid_grant", "error_codes": [70008]})
    )
    with pytest.raises(entra.FalhaAutenticacao, match="invalid_grant"):
        await entra.trocar_codigo("codigo", _fluxo(), http=http)


async def test_endpoint_inacessivel_vira_falha() -> None:
    def cair(pedido: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("sem rede", request=pedido)

    http = httpx.AsyncClient(transport=httpx.MockTransport(cair))
    with pytest.raises(entra.FalhaAutenticacao):
        await entra.trocar_codigo("codigo", _fluxo(), http=http)


async def test_overage_de_grupos_entra_sem_grupos() -> None:
    """Acima de 200 grupos o token não lista nenhum; o acesso cai ao mínimo."""
    token = _id_token(groups=None, _claim_names={"groups": "src1"})
    http = _cliente_token(httpx.Response(200, json={"id_token": token}))
    identidade = await entra.trocar_codigo("codigo", _fluxo(), http=http)
    assert identidade.grupos == ()
