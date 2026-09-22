"""Integração HTTP das oito rotas do painel de intenções.

A requisição atravessa o FastAPI de verdade — dependências, validação
de parâmetros, `response_model` — até um banco SQLite em arquivo semeado
no início do teste. O que se confere é o contrato que o frontend consome:
os campos e os nomes que os dublês de src/web/src/mocks/handlers.ts
prometem à interface, e a permissão que nenhuma rota pode afrouxar.

O banco é arquivo, e não memória, porque o `TestClient` roda a aplicação
num laço de eventos próprio: cada laço abre a sua conexão com o arquivo,
em vez de disputar uma conexão em memória criada no outro.
"""

import asyncio
import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.api import deps
from app.main import app
from app.persistence.models import Canal, Interacao
from app.persistence.sessao import obter_sessao
from app.persistence.tabelas import InteracaoTabela
from app.pipeline.desfechos import Desfecho
from app.pipeline.intencao import catalogo
from app.schemas.usuario import Perfil, Permissao, UsuarioAutenticado

pytestmark = pytest.mark.integracao

ANALISTA = UsuarioAutenticado(
    id="analista",
    nome="Analista do PMO",
    perfil=Perfil.LIDER_PROJETO,
    permissoes=frozenset({Permissao.VER_INTENCOES}),
)
SEM_PERMISSAO = UsuarioAutenticado(
    id="diretora",
    nome="Diretora",
    perfil=Perfil.DIRETORIA,
    permissoes=frozenset({Permissao.GERIR_ROTINAS}),
)

ROTAS = (
    "/intencoes/volume",
    "/intencoes/desfechos",
    "/intencoes/seguranca/resumo",
    "/intencoes/seguranca/serie",
    "/intencoes/catalogo/resumo",
    "/intencoes/catalogo/fora-de-escopo",
    "/intencoes/catalogo/baixa-confianca",
    "/intencoes/latencia",
)


def _interacao(
    *,
    dias_atras: float = 1,
    desfecho: Desfecho = Desfecho.ENCAMINHADA,
    intencao_id: str | None = "consultar_status_projeto",
    perfil: Perfil = Perfil.LIDER_PROJETO,
    prompt: str = "Qual o status do projeto da Linha 15-Prata?",
    confianca: float = 0.9,
) -> Interacao:
    return Interacao(
        id=str(uuid.uuid4()),
        conversa_id="conversa-teste",
        usuario_id="usuario-teste",
        perfil=perfil.value,
        canal=Canal.CHAT,
        prompt=prompt,
        resposta="Resposta registrada no teste.",
        intencao_id=intencao_id,
        confianca_intencao=confianca,
        desfecho=desfecho,
        latencia_ms=1500,
        criada_em=datetime.now(UTC) - timedelta(days=dias_atras),
        latencia_etapas={"injecao": 20, "abuso": 10, "intencao": 30, "executor": 1400},
    )


CARGA = [
    _interacao(),
    _interacao(),
    _interacao(intencao_id="consultar_riscos", perfil=Perfil.DIRETORIA),
    _interacao(intencao_id=None, desfecho=Desfecho.BLOQUEADA_INJECAO_REGRA),
    _interacao(intencao_id=None, desfecho=Desfecho.BLOQUEADA_ABUSO),
    _interacao(
        intencao_id=catalogo.FORA_DE_ESCOPO,
        desfecho=Desfecho.RECUSADA_FORA_ESCOPO,
        prompt="Qual o saldo do contrato?",
        confianca=0.3,
    ),
    _interacao(
        desfecho=Desfecho.RECUSADA_BAIXA_CONFIANCA,
        prompt="E o andamento daquele projeto?",
        confianca=0.4,
    ),
    # Fora da janela de 7 dias, dentro da de 30.
    _interacao(dias_atras=12, desfecho=Desfecho.BLOQUEADA_SAIDA),
]


async def _semear(url: str) -> None:
    engine = create_async_engine(url, poolclass=NullPool)
    async with engine.begin() as conexao:
        await conexao.run_sync(
            lambda s: InteracaoTabela.metadata.create_all(s, tables=[InteracaoTabela.__table__])
        )
    async with AsyncSession(engine) as sessao:
        sessao.add_all(InteracaoTabela.de_dominio(interacao) for interacao in CARGA)
        await sessao.commit()
    await engine.dispose()


@pytest.fixture
def cliente(tmp_path):
    url = f"sqlite+aiosqlite:///{(tmp_path / 'painel.db').as_posix()}"
    asyncio.run(_semear(url))
    engine = create_async_engine(url, poolclass=NullPool)

    async def sessao_de_teste() -> AsyncIterator[AsyncSession]:
        async with AsyncSession(engine, expire_on_commit=False) as sessao:
            yield sessao

    app.dependency_overrides[obter_sessao] = sessao_de_teste
    app.dependency_overrides[deps.obter_usuario_atual] = lambda: ANALISTA
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.clear()
        asyncio.run(engine.dispose())


# --- Permissão ------------------------------------------------------------------


@pytest.mark.parametrize("rota", ROTAS)
def test_rota_exige_ver_intencoes(cliente: TestClient, rota: str) -> None:
    """Autenticado sem a permissão recebe 403 em todas as rotas."""
    app.dependency_overrides[deps.obter_usuario_atual] = lambda: SEM_PERMISSAO

    resposta = cliente.get(rota)

    assert resposta.status_code == 403
    assert resposta.json()["detail"] == "Acesso restrito: requer ver_intencoes"


@pytest.mark.parametrize("rota", ROTAS)
def test_rota_responde_a_quem_tem_a_permissao(cliente: TestClient, rota: str) -> None:
    assert cliente.get(rota).status_code == 200


@pytest.mark.parametrize("rota", ROTAS)
def test_rota_recusa_janela_desconhecida(cliente: TestClient, rota: str) -> None:
    assert cliente.get(rota, params={"janela": "1d"}).status_code == 422


# --- Contrato de cada rota --------------------------------------------------------


def test_volume_traz_rotulo_e_preserva_as_zeradas(cliente: TestClient) -> None:
    corpo = cliente.get("/intencoes/volume", params={"janela": "7d"}).json()

    assert set(corpo[0]) == {"chave", "rotulo", "total"}
    assert corpo[0] == {
        "chave": "consultar_status_projeto",
        "rotulo": "Consultar status de projeto",
        "total": 3,
    }
    assert any(item["total"] == 0 for item in corpo)
    assert all(item["chave"] != catalogo.FORA_DE_ESCOPO for item in corpo)


def test_desfechos_trazem_os_oito_valores(cliente: TestClient) -> None:
    corpo = cliente.get("/intencoes/desfechos", params={"janela": "7d"}).json()

    assert [item["chave"] for item in corpo] == [d.value for d in Desfecho]
    por_chave = {item["chave"]: item for item in corpo}
    assert por_chave["encaminhada"] == {"chave": "encaminhada", "rotulo": "Atendida", "total": 3}
    assert por_chave["bloqueada_saida"]["total"] == 0


def test_resumo_de_seguranca(cliente: TestClient) -> None:
    corpo = cliente.get("/intencoes/seguranca/resumo", params={"janela": "7d"}).json()

    assert corpo == {
        "total_mensagens": 7,
        "bloqueios_injecao": 1,
        "bloqueios_abuso": 1,
        "bloqueios_saida": 0,
        "taxa_de_bloqueio": pytest.approx(2 / 7),
    }


def test_serie_separa_as_guardas(cliente: TestClient) -> None:
    corpo = cliente.get("/intencoes/seguranca/serie", params={"janela": "30d"}).json()

    assert [serie["nome"] for serie in corpo] == ["injecao", "abuso", "saida"]
    totais = {serie["nome"]: sum(p["total"] for p in serie["pontos"]) for serie in corpo}
    assert totais == {"injecao": 1, "abuso": 1, "saida": 1}
    ponto = corpo[0]["pontos"][0]
    assert set(ponto) == {"momento", "total"}
    datetime.fromisoformat(ponto["momento"])


def test_resumo_de_catalogo(cliente: TestClient) -> None:
    corpo = cliente.get("/intencoes/catalogo/resumo", params={"janela": "7d"}).json()

    assert corpo["intencoes_acionadas"] == 2
    assert corpo["enunciados_fora_de_escopo"] == 1
    assert corpo["enunciados_baixa_confianca"] == 1
    assert corpo["intencoes_sem_uso"] > 0


def test_fora_de_escopo(cliente: TestClient) -> None:
    [item] = cliente.get("/intencoes/catalogo/fora-de-escopo").json()

    assert set(item) == {"prompt", "ocorrencias", "ultima_em", "confianca_media"}
    assert item["prompt"] == "Qual o saldo do contrato?"
    assert item["confianca_media"] == pytest.approx(0.3)


def test_baixa_confianca(cliente: TestClient) -> None:
    [item] = cliente.get("/intencoes/catalogo/baixa-confianca").json()

    assert item["prompt"] == "E o andamento daquele projeto?"
    assert item["ocorrencias"] == 1


def test_latencia_traz_total_e_etapas(cliente: TestClient) -> None:
    corpo = cliente.get("/intencoes/latencia", params={"janela": "7d"}).json()

    assert corpo["p50"] == pytest.approx(1500)
    assert corpo["p95"] == pytest.approx(1500)
    etapas = {item["etapa"]: item for item in corpo["etapas"]}
    assert list(etapas) == ["injecao", "abuso", "intencao", "executor", "saida"]
    assert etapas["executor"]["p50"] == pytest.approx(1400)
    assert etapas["saida"]["amostras"] == 0


# --- Filtros ----------------------------------------------------------------------


def test_janela_de_7_dias_exclui_o_que_e_mais_antigo(cliente: TestClient) -> None:
    curta = cliente.get("/intencoes/seguranca/resumo", params={"janela": "7d"}).json()
    longa = cliente.get("/intencoes/seguranca/resumo", params={"janela": "30d"}).json()

    assert curta["bloqueios_saida"] == 0
    assert longa["bloqueios_saida"] == 1


def test_filtro_de_perfil(cliente: TestClient) -> None:
    corpo = cliente.get("/intencoes/volume", params={"janela": "7d", "perfil": "diretoria"}).json()

    assert sum(item["total"] for item in corpo) == 1
    assert corpo[0]["chave"] == "consultar_riscos"


def test_perfil_desconhecido_e_recusado(cliente: TestClient) -> None:
    resposta = cliente.get("/intencoes/volume", params={"perfil": "administrador"})

    assert resposta.status_code == 422
