"""Agregações do painel contra o PostgreSQL real.

Os testes unitários exercitam as consultas num SQLite em memória, e é a
restrição a SQL portável que torna isso válido. Este arquivo confere o
outro lado da equivalência: que as mesmas consultas rodam no servidor de
verdade, com `timestamptz`, `CHECK` e índices, e devolvem o mesmo número.

As interações são gravadas numa janela de 2001, onde nenhuma carga de
demonstração chega. Assim o teste não depende de o banco estar vazio, e
tudo é revertido no fim pela transação da fixture.

Pula limpo quando o banco não responde. Para rodar:

    docker compose -f infra/docker-compose.yml up -d db
    alembic upgrade head
"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics import consultas
from app.persistence.models import Canal, Conversa, Interacao
from app.persistence.repository import (
    ConversaRepository,
    InteracaoRepository,
    UsuarioRepository,
)
from app.persistence.sessao import criar_engine
from app.pipeline.desfechos import Desfecho
from app.schemas.usuario import Perfil

pytestmark = pytest.mark.integracao

FIM = datetime(2001, 3, 15, 12, 0, tzinfo=UTC)
INICIO = FIM - timedelta(days=7)
DENTRO = FIM - timedelta(days=1)


def _id(prefixo: str) -> str:
    return f"teste-{prefixo}-{uuid.uuid4().hex[:10]}"


@pytest.fixture
async def sessao():
    """Sessão numa transação revertida no fim, como em test_persistencia.py."""
    engine = criar_engine()
    try:
        conexao = await engine.connect()
    except Exception:  # noqa: BLE001 — qualquer falha de conexão pula a suíte
        await engine.dispose()
        pytest.skip(
            "PostgreSQL indisponível. Suba com "
            "`docker compose -f infra/docker-compose.yml up -d db`."
        )

    tabelas = await conexao.run_sync(lambda s: inspect(s).get_table_names())
    await conexao.rollback()
    if "interacao" not in tabelas:
        await conexao.close()
        await engine.dispose()
        pytest.skip("Esquema ausente. Rode `alembic upgrade head`.")

    transacao = await conexao.begin()
    aberta = AsyncSession(bind=conexao, expire_on_commit=False)
    try:
        yield aberta
    finally:
        await aberta.close()
        await transacao.rollback()
        await conexao.close()
        await engine.dispose()


@pytest.fixture
async def gravar(sessao: AsyncSession):
    """Grava interações de um usuário e de uma conversa criados para o teste."""
    usuario_id = _id("usuario")
    await UsuarioRepository(sessao).garantir(
        usuario_id, "Fernanda Medina", Perfil.DIRETORIA.value, f"{usuario_id}@exemplo.metro"
    )
    conversa = Conversa(
        id=_id("conversa"),
        usuario_id=usuario_id,
        conversa_externa_id=None,
        criada_em=INICIO,
        atualizada_em=INICIO,
    )
    await ConversaRepository(sessao).criar(conversa)
    repositorio = InteracaoRepository(sessao)

    async def _gravar(
        *,
        desfecho: Desfecho = Desfecho.ENCAMINHADA,
        intencao_id: str | None = "consultar_status_projeto",
        prompt: str = "Qual o status do projeto da Linha 15-Prata?",
        criada_em: datetime = DENTRO,
        latencia_ms: int = 1000,
    ) -> None:
        await repositorio.salvar(
            Interacao(
                id=_id("interacao"),
                conversa_id=conversa.id,
                usuario_id=usuario_id,
                perfil=Perfil.DIRETORIA.value,
                canal=Canal.VOZ,
                prompt=prompt,
                resposta="Resposta registrada no teste.",
                intencao_id=intencao_id,
                confianca_intencao=0.5,
                desfecho=desfecho,
                latencia_ms=latencia_ms,
                criada_em=criada_em,
            )
        )

    return _gravar


async def test_consultas_do_painel_rodam_no_postgresql(sessao, gravar) -> None:
    """As oito agregações devolvem no servidor o que devolvem no SQLite."""
    await gravar(latencia_ms=800)
    await gravar(latencia_ms=1200)
    await gravar(intencao_id=None, desfecho=Desfecho.BLOQUEADA_INJECAO_REGRA)
    await gravar(desfecho=Desfecho.RECUSADA_FORA_ESCOPO, intencao_id=None, prompt="Saldo?")
    await gravar(desfecho=Desfecho.RECUSADA_FORA_ESCOPO, intencao_id=None, prompt="saldo? ")
    await gravar(desfecho=Desfecho.RECUSADA_BAIXA_CONFIANCA, prompt="E aquele projeto?")

    volume = {
        linha.chave: linha.total
        for linha in await consultas.volume_por_intencao(sessao, INICIO, FIM)
    }
    assert volume["consultar_status_projeto"] == 3
    assert 0 in volume.values()

    desfechos = {
        linha.chave: linha.total
        for linha in await consultas.distribuicao_de_desfechos(sessao, INICIO, FIM)
    }
    assert desfechos[Desfecho.RECUSADA_FORA_ESCOPO.value] == 2

    serie = await consultas.serie_de_bloqueios(sessao, INICIO, FIM)
    assert sum(ponto.total for ponto in serie["injecao"]) == 1

    [fora] = await consultas.enunciados_fora_de_escopo(sessao, INICIO, FIM)
    assert fora.ocorrencias == 2
    assert fora.ultima_em.tzinfo is not None

    [hesitante] = await consultas.enunciados_baixa_confianca(sessao, INICIO, FIM)
    assert hesitante.prompt == "E aquele projeto?"

    medias = await consultas.confianca_media_por_intencao(sessao, INICIO, FIM)
    assert medias["consultar_status_projeto"] == pytest.approx(0.5)

    uso = {
        linha.chave: linha.total
        for linha in await consultas.volume_por_perfil_e_canal(sessao, INICIO, FIM)
    }
    assert uso["diretoria/voz"] == 6

    percentis = await consultas.latencia(sessao, INICIO, FIM, perfil=Perfil.DIRETORIA)
    assert percentis["p50"] == pytest.approx(1000)
