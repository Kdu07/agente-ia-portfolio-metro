"""Casos TNF-RNF04-01 a TNF-RNF04-04 do Projeto.md."""

import json
import uuid
from asyncio import timeout
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from sqlalchemy import func, inspect, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.api import deps
from app.auth import sessao as auth_sessao
from app.config import settings
from app.main import app
from app.persistence.repository import UsuarioRepository
from app.persistence.sessao import criar_engine, obter_sessao
from app.persistence.tabelas import InteracaoTabela
from app.pipeline import orquestrador as orq
from app.pipeline.guardas.abuso.classificador import ResultadoAbuso
from app.pipeline.guardas.injecao.classificador import ResultadoInjection
from app.pipeline.guardas.saida import ResultadoSaida
from app.pipeline.intencao.classificador import ResultadoIntencao
from app.rotinas.sonda import (
    AgenteIndisponivel,
    EstadoAmostra,
    FalhaObservador,
    ParadaProgramada,
    SondaHttp,
    medir_janela,
)
from app.schemas.usuario import Perfil, UsuarioAutenticado

INSTANTE = datetime(2026, 9, 22, 12, tzinfo=UTC)


async def _nao_dormir(_: float) -> None:
    return None


@pytest.fixture
async def banco_real() -> AsyncSession:
    """Transação PostgreSQL isolada para a passagem HTTP completa."""
    engine = criar_engine()
    try:
        async with timeout(3):
            conexao = await engine.connect()
    except Exception:  # noqa: BLE001 - ausência do serviço pula integração local
        await engine.dispose()
        pytest.skip("PostgreSQL indisponível; suba o serviço db do Docker Compose.")

    tabelas = await conexao.run_sync(lambda sync: inspect(sync).get_table_names())
    await conexao.rollback()
    necessarias = {"usuario", "sessao_usuario", "conversa", "interacao"}
    if not necessarias.issubset(tabelas):
        await conexao.close()
        await engine.dispose()
        pytest.skip("Esquema ausente ou desatualizado; rode `alembic upgrade head`.")

    transacao = await conexao.begin()
    sessao = AsyncSession(bind=conexao, expire_on_commit=False)
    try:
        yield sessao
    finally:
        await sessao.close()
        await transacao.rollback()
        await conexao.close()
        await engine.dispose()


@pytest.fixture
def pipeline_deterministico(monkeypatch: pytest.MonkeyPatch) -> None:
    """Isola serviços externos; HTTP, sessão e PostgreSQL continuam reais."""

    async def sem_injecao(_: str) -> ResultadoInjection:
        return ResultadoInjection(suspeita=False, confianca=0.0, motivo="limpo")

    async def sem_abuso(_: str) -> ResultadoAbuso:
        return ResultadoAbuso(abusiva=False, confianca=0.0)

    async def classificar(_: str) -> ResultadoIntencao:
        return ResultadoIntencao("consultar_status_projeto", 0.94)

    async def saida_limpa(_: str, __: str) -> ResultadoSaida:
        return ResultadoSaida(suspeita=False, confianca=0.0, motivo="limpo")

    monkeypatch.setattr(settings, "performance_mode", True)
    monkeypatch.setattr(settings, "session_secret", "segredo-exclusivo-da-sonda-rnf04")
    monkeypatch.setattr(orq.injecao_regras, "contem_padrao_suspeito", lambda _: False)
    monkeypatch.setattr(orq.injecao_classificador, "classificar", sem_injecao)
    monkeypatch.setattr(orq.abuso_classificador, "classificar", sem_abuso)
    monkeypatch.setattr(orq.intencao_classificador, "classificar", classificar)
    monkeypatch.setattr(orq.intencao_classificador, "limiar_de", lambda _: None)
    monkeypatch.setattr(orq.guarda_saida, "verificar", saida_limpa)


@pytest.mark.asyncio
async def test_tnf_rnf04_01_calcula_disponibilidade_sobre_janela_declarada() -> None:
    resultados = iter([None, None, AgenteIndisponivel("HTTP 503"), None])

    async def fluxo() -> None:
        resultado = next(resultados)
        if resultado is not None:
            raise resultado

    relatorio = await medir_janela(
        fluxo,
        total_amostras=4,
        intervalo_segundos=15,
        relogio=lambda: INSTANTE,
        dormir=_nao_dormir,
    )

    assert relatorio.total == 4
    assert relatorio.amostras_validas == 4
    assert relatorio.quantidade(EstadoAmostra.DISPONIVEL) == 3
    assert relatorio.quantidade(EstadoAmostra.INDISPONIVEL) == 1
    assert relatorio.percentual_disponibilidade == pytest.approx(75.0)
    assert relatorio.como_dict()["intervalo_segundos"] == 15


@pytest.mark.asyncio
async def test_tnf_rnf04_02_exclui_parada_programada_do_calculo() -> None:
    async def fluxo() -> None:
        raise AssertionError("o fluxo não deve rodar durante a parada")

    relatorio = await medir_janela(
        fluxo,
        total_amostras=1,
        intervalo_segundos=60,
        paradas_programadas=(
            ParadaProgramada(INSTANTE - timedelta(minutes=1), INSTANTE + timedelta(minutes=1)),
        ),
        relogio=lambda: INSTANTE,
    )

    assert relatorio.amostras_validas == 0
    assert relatorio.percentual_disponibilidade is None
    assert relatorio.quantidade(EstadoAmostra.PARADA_PROGRAMADA) == 1


@pytest.mark.asyncio
async def test_tnf_rnf04_03_falha_do_observador_e_inconclusiva() -> None:
    async def fluxo() -> None:
        raise FalhaObservador("configuração da sonda ausente")

    relatorio = await medir_janela(
        fluxo,
        total_amostras=1,
        intervalo_segundos=60,
        relogio=lambda: INSTANTE,
    )

    assert relatorio.amostras_validas == 0
    assert relatorio.percentual_disponibilidade is None
    assert relatorio.quantidade(EstadoAmostra.INCONCLUSIVA) == 1
    assert relatorio.amostras[0].detalhe == "configuração da sonda ausente"


@pytest.mark.asyncio
async def test_tnf_rnf04_04_exige_chat_e_turno_persistido() -> None:
    mensagem_recebida = ""

    def responder(request: httpx.Request) -> httpx.Response:
        nonlocal mensagem_recebida
        if request.url.path == "/chat":
            mensagem_recebida = __import__("json").loads(request.content)["mensagem"]
            return httpx.Response(
                200,
                json={
                    "resposta": "Projeto em andamento.",
                    "conversa_id": "conversa-sonda",
                    "desfecho": "encaminhada",
                    "bloqueada": False,
                },
            )
        return httpx.Response(
            200,
            json={"id": "conversa-sonda", "turnos": [{"prompt": mensagem_recebida}]},
        )

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(responder),
        base_url="https://agente.teste",
    ) as cliente:
        sonda = SondaHttp("https://agente.teste", "cookie-sintetico", cliente=cliente)
        relatorio = await medir_janela(
            sonda,
            total_amostras=1,
            intervalo_segundos=60,
            relogio=lambda: INSTANTE,
        )

    assert relatorio.quantidade(EstadoAmostra.DISPONIVEL) == 1
    assert relatorio.percentual_disponibilidade == pytest.approx(100.0)


@pytest.mark.integracao
@pytest.mark.asyncio
async def test_janela_local_atravessa_sessao_chat_e_postgresql(
    banco_real: AsyncSession,
    pipeline_deterministico: None,
) -> None:
    """Execução positiva da bancada sem substituir API ou persistência."""
    usuario = UsuarioAutenticado(
        id=f"sonda-rnf04-{uuid.uuid4().hex[:10]}",
        nome="Sonda sintética RNF04",
        email="sonda-rnf04@teste.local",
        perfil=Perfil.LIDER_PROJETO,
    )
    await UsuarioRepository(banco_real).garantir(
        usuario.id,
        usuario.nome,
        usuario.perfil.value,
        usuario.email,
    )
    _, cookie = await auth_sessao.criar(banco_real, usuario)

    async def fornecer_banco():
        yield banco_real

    app.dependency_overrides[obter_sessao] = fornecer_banco
    app.dependency_overrides[deps.obter_fabrica_sessoes] = lambda: async_sessionmaker(
        bind=banco_real.bind,
        expire_on_commit=False,
    )
    transporte = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    try:
        async with httpx.AsyncClient(
            transport=transporte,
            base_url="https://agente.teste",
        ) as cliente:
            sonda = SondaHttp("https://agente.teste", cookie, cliente=cliente)
            relatorio = await medir_janela(
                sonda,
                total_amostras=10,
                intervalo_segundos=1,
            )
    finally:
        app.dependency_overrides.clear()

    total_persistido = await banco_real.scalar(
        select(func.count())
        .select_from(InteracaoTabela)
        .where(InteracaoTabela.usuario_id == usuario.id)
    )
    print("RNF04_RESULTADO=" + json.dumps(relatorio.como_dict(), ensure_ascii=False))
    assert relatorio.total == 10
    assert relatorio.quantidade(EstadoAmostra.DISPONIVEL) == 10
    assert relatorio.quantidade(EstadoAmostra.INDISPONIVEL) == 0
    assert relatorio.quantidade(EstadoAmostra.INCONCLUSIVA) == 0
    assert relatorio.percentual_disponibilidade == pytest.approx(100.0)
    assert total_persistido == 10


@pytest.mark.asyncio
async def test_banco_indisponivel_derruba_amostra_mesmo_com_http_ativo() -> None:
    def responder(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/chat":
            return httpx.Response(500, json={"detail": "banco indisponível"})
        raise AssertionError("histórico não deveria ser consultado")

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(responder),
        base_url="https://agente.teste",
    ) as cliente:
        sonda = SondaHttp("https://agente.teste", "cookie-sintetico", cliente=cliente)
        relatorio = await medir_janela(
            sonda,
            total_amostras=1,
            intervalo_segundos=60,
            relogio=lambda: INSTANTE,
        )

    assert relatorio.quantidade(EstadoAmostra.INDISPONIVEL) == 1
    assert relatorio.percentual_disponibilidade == pytest.approx(0.0)


@pytest.mark.parametrize(
    ("total", "intervalo"),
    [(0, 1), (1, -1)],
)
@pytest.mark.asyncio
async def test_parametros_invalidos_nao_produzem_relatorio(total: int, intervalo: float) -> None:
    async def fluxo() -> None:
        return None

    with pytest.raises(ValueError):
        await medir_janela(
            fluxo,
            total_amostras=total,
            intervalo_segundos=intervalo,
        )
