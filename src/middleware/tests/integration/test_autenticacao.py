"""Teste de integração do login: /auth/login -> callback -> sessão -> logout.

O Entra ID é dublado em `entra.trocar_codigo` — o que ele valida está
coberto em tests/unit/test_entra.py. O que se verifica aqui é a costura:
o cookie do fluxo, o `state`, a projeção do usuário, a sessão gravada no
PostgreSQL e a revogação no logout.

A parte que grava sessão precisa do banco e pula limpa sem ele, como
tests/integration/test_persistencia.py. Cada teste roda numa transação
revertida no fim; o `commit` do callback vira um savepoint dentro dela.
"""

from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import inspect, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import entra
from app.config import settings
from app.main import app
from app.persistence.sessao import criar_engine, obter_sessao
from app.persistence.tabelas import SessaoUsuarioTabela

IDENTIDADE = entra.IdentidadeEntra(
    oid="teste-oid-auth",
    nome="Fernanda Medina",
    email="teste-auth@metro.example",
    grupos=("g-lider", "g-intencoes"),
)


@pytest.fixture(autouse=True)
def ambiente(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "entra_tenant_id", "11111111-2222-3333-4444-555555555555")
    monkeypatch.setattr(settings, "entra_client_id", "cliente")
    monkeypatch.setattr(settings, "entra_client_secret", "segredo")
    monkeypatch.setattr(settings, "session_secret", "segredo-de-sessao")
    # O TestClient fala http; um cookie Secure não voltaria nas requisições.
    monkeypatch.setattr(settings, "session_cookie_secure", False)
    monkeypatch.setattr(settings, "entra_grupo_lider_projeto", "g-lider")
    monkeypatch.setattr(settings, "entra_grupo_ver_intencoes", "g-intencoes")


@pytest.fixture
def cliente():
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture
async def banco():
    """Sessão numa transação revertida; commits viram savepoints.

    Usada com `cliente_assincrono`, e não com o `TestClient`: o TestClient
    roda a aplicação no event loop de outra thread, e a conexão asyncpg
    aberta aqui só funciona no loop do teste.
    """
    engine = criar_engine()
    try:
        conexao = await engine.connect()
    except Exception:  # noqa: BLE001 — qualquer falha de conexão pula
        await engine.dispose()
        pytest.skip("PostgreSQL indisponível.")

    tabelas = await conexao.run_sync(lambda s: inspect(s).get_table_names())
    await conexao.rollback()
    if "sessao_usuario" not in tabelas:
        await conexao.close()
        await engine.dispose()
        pytest.skip("Esquema ausente. Rode `alembic upgrade head`.")

    transacao = await conexao.begin()
    sessao = AsyncSession(
        bind=conexao, expire_on_commit=False, join_transaction_mode="create_savepoint"
    )

    async def _obter():
        yield sessao

    app.dependency_overrides[obter_sessao] = _obter
    try:
        yield sessao
    finally:
        await sessao.close()
        await transacao.rollback()
        await conexao.close()
        await engine.dispose()


@pytest.fixture
async def cliente_assincrono(banco: AsyncSession):
    transporte = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transporte, base_url="http://testserver") as client:
        yield client
    app.dependency_overrides.clear()


def _state_de(resposta: httpx.Response) -> str:
    assert resposta.status_code == 302
    return parse_qs(urlparse(resposta.headers["location"]).query)["state"][0]


def _iniciar_login(client: TestClient) -> str:
    """Faz o /auth/login e devolve o `state` que foi ao Entra."""
    return _state_de(client.get("/auth/login", follow_redirects=False))


def _dublar_entra(monkeypatch: pytest.MonkeyPatch, recebidos: list | None = None) -> None:
    async def _trocar(codigo: str, fluxo: entra.FluxoPendente, **_) -> entra.IdentidadeEntra:
        if recebidos is not None:
            recebidos.append((codigo, fluxo))
        return IDENTIDADE

    monkeypatch.setattr(entra, "trocar_codigo", _trocar)


# --- Sem banco -----------------------------------------------------------


def test_login_redireciona_ao_tenant_com_cookie_de_fluxo(cliente: TestClient) -> None:
    resposta = cliente.get("/auth/login", follow_redirects=False)

    assert resposta.status_code == 302
    assert resposta.headers["location"].startswith(
        "https://login.microsoftonline.com/11111111-2222-3333-4444-555555555555/"
    )
    cookie = resposta.headers["set-cookie"]
    assert cookie.startswith("fluxo_login=")
    assert "HttpOnly" in cookie
    assert "SameSite=lax" in cookie
    assert "Path=/" in cookie


def test_login_sem_configuracao_devolve_503(
    cliente: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "entra_tenant_id", "")
    assert cliente.get("/auth/login", follow_redirects=False).status_code == 503


def test_callback_sem_cookie_de_fluxo_e_400(cliente: TestClient) -> None:
    resposta = cliente.get("/auth/callback", params={"code": "c", "state": "s"})
    assert resposta.status_code == 400


def test_callback_com_state_alheio_e_400(cliente: TestClient) -> None:
    _iniciar_login(cliente)
    resposta = cliente.get(
        "/auth/callback", params={"code": "c", "state": "forjado"}, follow_redirects=False
    )
    assert resposta.status_code == 400


def test_recusa_do_entra_volta_a_tela_de_entrada(cliente: TestClient) -> None:
    state = _iniciar_login(cliente)
    resposta = cliente.get(
        "/auth/callback",
        params={"state": state, "error": "access_denied"},
        follow_redirects=False,
    )
    assert resposta.status_code == 303
    assert resposta.headers["location"] == "/entrar?erro=login"
    assert "sessao=" not in resposta.headers.get("set-cookie", "")


def test_token_recusado_volta_a_tela_de_entrada(
    cliente: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def _recusar(*_, **__):
        raise entra.FalhaAutenticacao("nonce não confere")

    monkeypatch.setattr(entra, "trocar_codigo", _recusar)
    state = _iniciar_login(cliente)
    resposta = cliente.get(
        "/auth/callback", params={"state": state, "code": "c"}, follow_redirects=False
    )
    assert resposta.status_code == 303
    assert resposta.headers["location"] == "/entrar?erro=login"


def test_cookie_de_sessao_forjado_e_401(cliente: TestClient) -> None:
    cliente.cookies.set("sessao", "qualquer.coisa.assinada")
    assert cliente.get("/auth/eu").status_code == 401


# --- Com banco -----------------------------------------------------------


async def test_fluxo_completo_de_login_e_logout(
    cliente_assincrono: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    cliente = cliente_assincrono
    recebidos: list = []
    _dublar_entra(monkeypatch, recebidos)

    state = _state_de(await cliente.get("/auth/login"))
    resposta = await cliente.get("/auth/callback", params={"state": state, "code": "codigo-1"})

    assert resposta.status_code == 303
    assert resposta.headers["location"] == "/"
    cookies = resposta.headers.get_list("set-cookie")
    sessao = next(c for c in cookies if c.startswith("sessao="))
    assert "HttpOnly" in sessao
    assert "SameSite=strict" in sessao
    # O cookie do fluxo é descartado assim que cumpre o papel.
    assert any(c.startswith("fluxo_login=") and "Max-Age=0" in c for c in cookies)
    # O code_verifier que chegou à troca é o mesmo gerado no /login.
    assert recebidos[0][0] == "codigo-1"
    assert recebidos[0][1].estado == state

    eu = await cliente.get("/auth/eu")
    assert eu.status_code == 200
    assert eu.json() == {
        "id": "teste-oid-auth",
        "nome": "Fernanda Medina",
        "email": "teste-auth@metro.example",
        "perfil": "lider_projeto",
        "permissoes": ["ver_intencoes"],
    }

    valor_antigo = cliente.cookies["sessao"]
    assert (await cliente.post("/auth/logout")).status_code == 204
    assert (await cliente.get("/auth/eu")).status_code == 401

    # Revogação no servidor: o cookie copiado antes do logout não vale mais.
    cliente.cookies.set("sessao", valor_antigo)
    assert (await cliente.get("/auth/eu")).status_code == 401


async def test_sessao_vencida_no_servidor_e_401(
    cliente_assincrono: httpx.AsyncClient,
    banco: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cliente = cliente_assincrono
    _dublar_entra(monkeypatch)
    state = _state_de(await cliente.get("/auth/login"))
    await cliente.get("/auth/callback", params={"state": state, "code": "c"})
    assert (await cliente.get("/auth/eu")).status_code == 200

    await banco.execute(
        update(SessaoUsuarioTabela)
        .where(SessaoUsuarioTabela.usuario_id == IDENTIDADE.oid)
        .values(expira_em=datetime.now(UTC) - timedelta(minutes=1))
    )
    assert (await cliente.get("/auth/eu")).status_code == 401


def test_logout_sem_sessao_e_idempotente(cliente: TestClient) -> None:
    assert cliente.post("/auth/logout").status_code == 204
