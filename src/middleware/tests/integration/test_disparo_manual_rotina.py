"""Disparo HTTP com autenticação e sessões independentes em PostgreSQL real.

Use um banco de testes migrado (`alembic upgrade head`). A fixture confirma
transações e remove somente seus registros ao final: compartilhar uma conexão
ou reverter uma única transação esconderia o bloqueio da #539. Apenas o Graph
e o processamento do prompt são controlados; os dois upserts são reais.
"""

import asyncio
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, inspect, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.api.routes import rotinas as rotas
from app.auth import entra
from app.auth import sessao as auth_sessao
from app.config import settings
from app.persistence import sessao as persistencia
from app.persistence.models import Canal, Conversa, Interacao, Rotina, StatusExecucao
from app.persistence.repository import (
    ConversaRepository,
    ExecucaoRepository,
    InteracaoRepository,
    RotinaRepository,
    UsuarioRepository,
)
from app.persistence.tabelas import (
    ConversaTabela,
    ExecucaoRotinaTabela,
    InteracaoTabela,
    RotinaTabela,
    SessaoUsuarioTabela,
    UsuarioTabela,
)
from app.pipeline.desfechos import Desfecho
from app.rotinas import execucao
from app.schemas.chat import ChatResponse
from app.schemas.usuario import Perfil, Permissao, UsuarioAutenticado

pytestmark = pytest.mark.integracao


@dataclass
class Cenario:
    fabrica: async_sessionmaker[AsyncSession]
    usuario: UsuarioAutenticado
    rotina: Rotina
    cookie: str
    graph: AsyncMock
    processar: AsyncMock


@pytest.fixture
async def cenario(monkeypatch):
    engine = persistencia.criar_engine()
    try:
        async with engine.connect() as conexao:
            tabelas = await conexao.run_sync(lambda c: inspect(c).get_table_names())
    except Exception:  # noqa: BLE001 — mesma convenção da suíte de persistência
        await engine.dispose()
        pytest.skip("PostgreSQL indisponível. Use um banco de testes migrado.")
    if "sessao_usuario" not in tabelas:
        await engine.dispose()
        pytest.skip("Esquema ausente. Rode `alembic upgrade head` no banco de testes.")

    fabrica = async_sessionmaker(engine, expire_on_commit=False)
    monkeypatch.setattr(persistencia, "fabrica_de_sessoes", lambda: fabrica)
    monkeypatch.setattr(execucao, "fabrica_de_sessoes", lambda: fabrica)
    monkeypatch.setattr(settings, "session_secret", "segredo-sintetico-issue539")
    monkeypatch.setattr(settings, "entra_grupo_lider_projeto", "teste-lider-539")
    monkeypatch.setattr(settings, "entra_grupo_gerir_rotinas", "teste-rotinas-539")
    usuario = UsuarioAutenticado(
        id=f"teste-539-{uuid.uuid4()}",
        nome="Dono no login",
        perfil=Perfil.LIDER_PROJETO,
        permissoes=frozenset({Permissao.GERIR_ROTINAS}),
    )
    agora = datetime.now(UTC)
    rotina = Rotina(
        id=str(uuid.uuid4()),
        nome="Disparo manual #539",
        prompt="Qual o status do projeto?",
        agenda_cron="0 8 * * mon-fri",
        timezone="America/Sao_Paulo",
        dono_id=usuario.id,
        ativa=True,
        criada_em=agora,
        atualizada_em=agora,
    )
    graph = AsyncMock(
        return_value=entra.IdentidadeEntra(
            oid=usuario.id,
            nome="Dono confirmado no Entra",
            email=None,
            grupos=("teste-lider-539", "teste-rotinas-539"),
        )
    )
    monkeypatch.setattr(entra, "consultar_usuario", graph)

    async def processar(rotina, dono):
        assert dono.id == usuario.id
        assert dono.nome == "Dono confirmado no Entra"
        assert dono.pode(Permissao.GERIR_ROTINAS)
        conversa = Conversa(
            id=str(uuid.uuid4()),
            usuario_id=dono.id,
            conversa_externa_id=None,
            criada_em=agora,
            atualizada_em=agora,
        )
        interacao = Interacao(
            id=str(uuid.uuid4()),
            conversa_id=conversa.id,
            usuario_id=dono.id,
            perfil=dono.perfil.value,
            canal=Canal.ROTINA,
            prompt=rotina.prompt,
            resposta="Resultado controlado do disparo manual.",
            intencao_id="consultar_status_projeto",
            confianca_intencao=0.91,
            desfecho=Desfecho.ENCAMINHADA,
            latencia_ms=1,
            criada_em=agora,
            rotina_id=rotina.id,
        )
        async with fabrica() as banco:
            await ConversaRepository(banco).criar(conversa)
            await InteracaoRepository(banco).salvar(interacao)
            await banco.commit()
        return ChatResponse(
            resposta=interacao.resposta,
            conversa_id=conversa.id,
            desfecho=interacao.desfecho.value,
            interacao_id=interacao.id,
        )

    processamento = AsyncMock(side_effect=processar)
    monkeypatch.setattr(execucao, "_processar", processamento)
    try:
        async with fabrica() as banco:
            await UsuarioRepository(banco).garantir(usuario.id, usuario.nome, usuario.perfil.value)
            _, cookie = await auth_sessao.criar(banco, usuario)
            await RotinaRepository(banco).criar(rotina)
            await banco.commit()
        yield Cenario(fabrica, usuario, rotina, cookie, graph, processamento)
    finally:
        async with fabrica() as banco:
            for tabela, filtro in (
                (ExecucaoRotinaTabela, ExecucaoRotinaTabela.rotina_id == rotina.id),
                (InteracaoTabela, InteracaoTabela.usuario_id == usuario.id),
                (ConversaTabela, ConversaTabela.usuario_id == usuario.id),
                (RotinaTabela, RotinaTabela.id == rotina.id),
                (SessaoUsuarioTabela, SessaoUsuarioTabela.usuario_id == usuario.id),
                (UsuarioTabela, UsuarioTabela.id == usuario.id),
            ):
                await banco.execute(delete(tabela).where(filtro))
            await banco.commit()
        await engine.dispose()


async def _disparar(cenario, rotina_id=None):
    app = FastAPI()
    app.include_router(rotas.router)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://teste") as cliente:
        cliente.cookies.set(auth_sessao.NOME_COOKIE, cenario.cookie)
        # Antes da correção, o segundo upsert espera o lock da requisição
        # e este limite falha com TimeoutError, mesmo com o Graph respondendo.
        return await asyncio.wait_for(
            cliente.post(f"/rotinas/{rotina_id or cenario.rotina.id}/executar"),
            timeout=5,
        )


async def test_disparo_manual_conclui_com_dono_confirmado(cenario):
    resposta = await _disparar(cenario)
    assert resposta.status_code == 200, resposta.text
    dados = resposta.json()
    assert dados["status"] == "sucesso"
    assert dados["concluida_em"] is not None
    assert dados["resposta"] == "Resultado controlado do disparo manual."
    cenario.graph.assert_awaited_once_with(cenario.usuario.id)
    cenario.processar.assert_awaited_once()
    async with cenario.fabrica() as banco:
        registro = await ExecucaoRepository(banco).obter_com_interacao(dados["id"])
        assert registro is not None
        disparo, interacao = registro
        assert disparo.status is StatusExecucao.SUCESSO
        assert interacao is not None and interacao.canal is Canal.ROTINA
        assert interacao.rotina_id == cenario.rotina.id
        nome = await banco.scalar(
            select(UsuarioTabela.nome).where(
                UsuarioTabela.id == cenario.usuario.id,
            )
        )
        assert nome == "Dono confirmado no Entra"


@pytest.mark.parametrize(
    "falha,status,ativa",
    [
        (entra.UsuarioEntraInativo("Dono inativo"), 403, False),
        (entra.FalhaConsultaDiretorio("Graph indisponível"), 503, True),
        (None, 403, False),
    ],
)
async def test_falha_de_confirmacao_preserva_autorizacao_e_auditoria(cenario, falha, status, ativa):
    if falha is None:
        cenario.graph.return_value = entra.IdentidadeEntra(
            oid=cenario.usuario.id,
            nome="Dono",
            email=None,
            grupos=("teste-lider-539",),
        )
    else:
        cenario.graph.side_effect = falha
    resposta = await _disparar(cenario)
    assert resposta.status_code == status, resposta.text
    cenario.processar.assert_not_awaited()
    async with cenario.fabrica() as banco:
        rotina = await RotinaRepository(banco).obter(cenario.rotina.id)
        assert rotina is not None and rotina.ativa is ativa
        registros = await ExecucaoRepository(banco).listar_por_rotina(cenario.rotina.id)
        assert len(registros) == 1
        assert registros[0].status is StatusExecucao.FALHA
        assert registros[0].concluida_em is not None


async def test_rotina_alheia_nao_consulta_entra_nem_inicia_execucao(cenario):
    # Uma rotina do mesmo dono deixa de pertencer ao solicitante autenticado.
    async with cenario.fabrica() as banco:
        await banco.execute(
            delete(SessaoUsuarioTabela).where(
                SessaoUsuarioTabela.usuario_id == cenario.usuario.id,
            )
        )
        outro = UsuarioAutenticado(
            id=f"teste-539-outro-{uuid.uuid4()}",
            nome="Outro usuário",
            perfil=Perfil.LIDER_PROJETO,
            permissoes=cenario.usuario.permissoes,
        )
        await UsuarioRepository(banco).garantir(outro.id, outro.nome, outro.perfil.value)
        _, cookie = await auth_sessao.criar(banco, outro)
        await banco.commit()
    try:
        cenario.cookie = cookie
        resposta = await _disparar(cenario)
        assert resposta.status_code == 404
        cenario.graph.assert_not_awaited()
        cenario.processar.assert_not_awaited()
        async with cenario.fabrica() as banco:
            assert await ExecucaoRepository(banco).listar_por_rotina(cenario.rotina.id) == []
    finally:
        async with cenario.fabrica() as banco:
            await banco.execute(delete(UsuarioTabela).where(UsuarioTabela.id == outro.id))
            await banco.commit()
