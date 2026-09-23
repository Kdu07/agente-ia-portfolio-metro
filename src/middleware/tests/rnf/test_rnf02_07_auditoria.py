"""Casos TNF-RNF02 e TNF-RNF07 contra o registro persistido."""

import os
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import func, inspect, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.persistence.auditoria import expurgar_interacoes, medir_rastreabilidade
from app.persistence.models import Canal, Interacao
from app.persistence.repository import InteracaoRepository, UsuarioRepository
from app.persistence.tabelas import (
    Base,
    ConversaTabela,
    InteracaoTabela,
    RotinaTabela,
    UsuarioTabela,
)
from app.pipeline.desfechos import Desfecho
from app.schemas.usuario import Perfil

AGORA = datetime(2026, 9, 23, 12, tzinfo=UTC)
USUARIO = f"rnf02-{uuid4().hex}"
OUTRO_USUARIO = f"rnf02-outro-{uuid4().hex}"
CONVERSA = f"rnf02-conversa-{uuid4().hex}"
ROTINA = f"rnf02-rotina-{uuid4().hex}"


@pytest.fixture
async def banco() -> AsyncSession:
    """Usa PostgreSQL quando RNF_DATABASE_URL estiver definido; SQLite é fallback."""
    url = os.getenv("RNF_DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    engine = create_async_engine(url)
    conexao = await engine.connect()
    transacao = await conexao.begin()
    if url.startswith("sqlite"):
        await conexao.run_sync(
            lambda sync: Base.metadata.create_all(
                sync,
                tables=[
                    UsuarioTabela.__table__,
                    ConversaTabela.__table__,
                    InteracaoTabela.__table__,
                ],
            )
        )
    else:
        tabelas = await conexao.run_sync(lambda sync: inspect(sync).get_table_names())
        necessarias = {"usuario", "conversa", "interacao"}
        if not necessarias.issubset(tabelas):
            await transacao.rollback()
            await conexao.close()
            await engine.dispose()
            pytest.skip("PostgreSQL sem as migrations necessárias.")
    sessao = AsyncSession(bind=conexao, expire_on_commit=False)
    try:
        for usuario_id in (USUARIO, OUTRO_USUARIO):
            await UsuarioRepository(sessao).garantir(
                usuario_id,
                "Usuário de teste",
                Perfil.LIDER_PROJETO.value,
                f"{usuario_id}@teste.local",
            )
        sessao.add(
            ConversaTabela(
                id=CONVERSA,
                usuario_id=USUARIO,
                criada_em=AGORA,
                atualizada_em=AGORA,
            )
        )
        sessao.add(
            RotinaTabela(
                id=ROTINA,
                nome="Rotina de teste",
                prompt="Consultar status do projeto",
                agenda_cron="0 8 * * *",
                timezone="America/Sao_Paulo",
                dono_id=USUARIO,
                criada_em=AGORA,
                atualizada_em=AGORA,
            )
        )
        await sessao.flush()
        yield sessao
    finally:
        await sessao.close()
        await transacao.rollback()
        await conexao.close()
    await engine.dispose()


def interacao(
    *,
    identificador: str,
    desfecho: Desfecho = Desfecho.ENCAMINHADA,
    canal: Canal = Canal.CHAT,
    criada_em: datetime = AGORA,
    usuario_id: str = USUARIO,
    rotina_id: str | None = None,
) -> Interacao:
    return Interacao(
        id=identificador,
        conversa_id=CONVERSA,
        usuario_id=usuario_id,
        perfil=Perfil.LIDER_PROJETO.value,
        canal=canal,
        prompt=f"prompt-{identificador}",
        resposta="resposta sintetica",
        intencao_id="consultar_status_projeto",
        confianca_intencao=0.95,
        desfecho=desfecho,
        latencia_ms=20,
        criada_em=criada_em,
        rotina_id=rotina_id,
    )


@pytest.mark.asyncio
async def test_tnf_rnf02_01_cobertura_de_autoria_origem_e_momento(banco: AsyncSession) -> None:
    repo = InteracaoRepository(banco)
    await repo.salvar(interacao(identificador="chat"))
    await repo.salvar(
        interacao(
            identificador="rotina",
            canal=Canal.ROTINA,
            rotina_id=ROTINA,
        )
    )
    await banco.flush()

    resultado = await medir_rastreabilidade(banco, usuario_ids=frozenset({USUARIO}))

    assert resultado.efetivadas == 2
    assert resultado.completas == 2
    assert resultado.cobertura_percentual == pytest.approx(100.0)


@pytest.mark.asyncio
async def test_tnf_rnf02_02_registro_sem_origem_reprova(banco: AsyncSession) -> None:
    linha = InteracaoTabela.de_dominio(
        interacao(identificador="incompleta", canal=Canal.ROTINA)
    )
    banco.add(linha)
    await banco.flush()

    resultado = await medir_rastreabilidade(banco, usuario_ids=frozenset({USUARIO}))

    assert resultado.efetivadas == 1
    assert resultado.completas == 0
    assert resultado.cobertura_percentual < 100.0


@pytest.mark.asyncio
async def test_tnf_rnf02_03_rotina_preserva_vinculo_do_disparo(banco: AsyncSession) -> None:
    await InteracaoRepository(banco).salvar(
        interacao(identificador="rotina-vinculada", canal=Canal.ROTINA, rotina_id=ROTINA)
    )
    await banco.flush()

    linha = await banco.scalar(
        select(InteracaoTabela).where(InteracaoTabela.id == "rotina-vinculada")
    )

    assert linha is not None
    assert linha.canal == Canal.ROTINA.value
    assert linha.rotina_id == ROTINA


@pytest.mark.asyncio
async def test_tnf_rnf02_04_nao_efetivada_fica_fora_do_denominador(
    banco: AsyncSession,
) -> None:
    repo = InteracaoRepository(banco)
    await repo.salvar(interacao(identificador="efetivada"))
    await repo.salvar(
        interacao(identificador="cancelada", desfecho=Desfecho.RECUSADA_FORA_ESCOPO)
    )
    await banco.flush()

    resultado = await medir_rastreabilidade(banco, usuario_ids=frozenset({USUARIO}))

    assert resultado.efetivadas == 1
    assert resultado.cobertura_percentual == pytest.approx(100.0)


@pytest.mark.asyncio
async def test_tnf_rnf07_01_registro_tem_controle_de_acesso_por_usuario(
    banco: AsyncSession,
) -> None:
    await InteracaoRepository(banco).salvar(interacao(identificador="privada"))
    await banco.flush()

    propria = await InteracaoRepository(banco).listar_por_usuario(USUARIO)
    alheia = await InteracaoRepository(banco).listar_por_usuario(OUTRO_USUARIO)

    assert [item.id for item in propria] == ["privada"]
    assert alheia == []


@pytest.mark.asyncio
async def test_tnf_rnf07_02_expurgo_remove_registro_fora_do_prazo(
    banco: AsyncSession,
) -> None:
    await InteracaoRepository(banco).salvar(
        interacao(identificador="vencida", criada_em=AGORA - timedelta(days=31))
    )
    await InteracaoRepository(banco).salvar(
        interacao(identificador="vigente", criada_em=AGORA - timedelta(days=29))
    )
    await banco.flush()

    removidas = await expurgar_interacoes(
        banco, agora=AGORA, dias_retencao=30, usuario_ids=frozenset({USUARIO})
    )
    await banco.flush()
    ids = await banco.scalars(
        select(InteracaoTabela.id)
        .where(InteracaoTabela.usuario_id == USUARIO)
        .order_by(InteracaoTabela.id)
    )

    assert removidas == 1
    assert list(ids) == ["vigente"]


@pytest.mark.asyncio
async def test_tnf_rnf07_03_registro_na_borda_ainda_e_preservado(
    banco: AsyncSession,
) -> None:
    await InteracaoRepository(banco).salvar(
        interacao(identificador="borda", criada_em=AGORA - timedelta(days=30))
    )
    await banco.flush()

    removidas = await expurgar_interacoes(
        banco, agora=AGORA, dias_retencao=30, usuario_ids=frozenset({USUARIO})
    )

    assert removidas == 0
    assert (
        await banco.scalar(
            select(func.count())
            .select_from(InteracaoTabela)
            .where(InteracaoTabela.usuario_id == USUARIO)
        )
        == 1
    )


@pytest.mark.asyncio
async def test_tnf_rnf07_04_expurgo_nao_remove_registro_vigente(
    banco: AsyncSession,
) -> None:
    await InteracaoRepository(banco).salvar(
        interacao(identificador="vigente", criada_em=AGORA - timedelta(days=1))
    )
    await banco.flush()

    removidas = await expurgar_interacoes(
        banco, agora=AGORA, dias_retencao=30, usuario_ids=frozenset({USUARIO})
    )

    assert removidas == 0
    assert (
        await banco.scalar(
            select(func.count())
            .select_from(InteracaoTabela)
            .where(InteracaoTabela.usuario_id == USUARIO)
        )
        == 1
    )
