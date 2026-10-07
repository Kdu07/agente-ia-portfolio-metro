"""As sessões que a suíte de integração da interface usa (#471).

O `scripts/sessoes_integracao.py` abre uma sessão válida e uma vencida
para o `demo-roberto`. A interface só exercita a sessão expirada de verdade
se o middleware de fato recusar a segunda; é isso que se verifica aqui,
pelo mesmo `resolver` que a dependência `obter_usuario_atual` usa.

Precisa do PostgreSQL e pula limpo sem ele. Roda numa transação revertida.
"""

import pytest
from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import sessao as auth_sessao
from app.config import settings
from app.persistence.sessao import criar_engine
from app.schemas.usuario import Permissao
from scripts.sessoes_integracao import USUARIO_ID, abrir_sessoes


@pytest.fixture(autouse=True)
def segredo(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "session_secret", "segredo-da-suite-de-integracao")


@pytest.fixture
async def banco():
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
    try:
        yield sessao
    finally:
        await sessao.close()
        await transacao.rollback()
        await conexao.close()
        await engine.dispose()


@pytest.mark.integracao
async def test_sessao_valida_resolve_com_as_permissoes_das_telas(banco: AsyncSession) -> None:
    cookies = await abrir_sessoes(banco)

    sessao = await auth_sessao.resolver(banco, cookies["sessao"])

    assert sessao is not None
    assert sessao.usuario.id == USUARIO_ID
    assert sessao.usuario.permissoes == {Permissao.VER_INTENCOES, Permissao.GERIR_ROTINAS}


@pytest.mark.integracao
async def test_sessao_expirada_e_recusada_pelo_middleware(banco: AsyncSession) -> None:
    cookies = await abrir_sessoes(banco)

    assert cookies["sessao_expirada"] != cookies["sessao"]
    assert await auth_sessao.resolver(banco, cookies["sessao_expirada"]) is None
