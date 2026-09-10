"""Integração do pipeline de NLP com a persistência PostgreSQL."""

import uuid
from asyncio import timeout
from datetime import UTC, datetime

import pytest
from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import AsyncSession

from app.copilot.client import RespostaCopilot
from app.persistence.models import Canal
from app.persistence.repository import ConversaRepository, InteracaoRepository, UsuarioRepository
from app.persistence.sessao import criar_engine
from app.pipeline import orquestrador as orq
from app.pipeline.desfechos import Desfecho
from app.pipeline.guardas.abuso.classificador import ResultadoAbuso
from app.pipeline.guardas.injecao.classificador import ResultadoInjection
from app.pipeline.guardas.saida import ResultadoSaida
from app.pipeline.intencao.classificador import ResultadoIntencao
from app.pipeline.orquestrador import Orquestrador
from app.schemas.chat import ChatRequest
from app.schemas.usuario import Perfil, UsuarioAutenticado


class CopilotFalso:
    async def enviar(self, texto, intencao_id, exige_confirmacao, conversa_externa_id=None):
        return RespostaCopilot(
            texto="O Projeto Verde está com 60% de avanço.",
            conversa_externa_id="conversa-externa-teste",
        )


@pytest.fixture
async def sessao_banco() -> AsyncSession:
    """Abre uma transação real e desfaz todos os dados ao final."""
    engine = criar_engine()
    try:
        async with timeout(3):
            conexao = await engine.connect()
    except Exception:  # noqa: BLE001
        await engine.dispose()
        pytest.skip("PostgreSQL indisponível; suba o serviço db do Docker Compose.")

    tabelas = await conexao.run_sync(lambda sync: inspect(sync).get_table_names())
    await conexao.rollback()
    if "interacao" not in tabelas:
        await conexao.close()
        await engine.dispose()
        pytest.skip("Esquema ausente; rode `alembic upgrade head`.")

    transacao = await conexao.begin()
    sessao = AsyncSession(bind=conexao, expire_on_commit=False)
    try:
        yield sessao
    finally:
        await sessao.close()
        await transacao.rollback()
        await conexao.close()
        await engine.dispose()


async def test_pipeline_grava_e_recupera_resultado_do_nlp(
    sessao_banco: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Persiste a saída do NLP e a recupera por conversa e usuário."""
    usuario = UsuarioAutenticado(
        id=f"teste-nlp-{uuid.uuid4().hex[:10]}",
        nome="Usuária de teste",
        perfil=Perfil.LIDER_PROJETO,
        email="nlp@exemplo.metro",
    )
    await UsuarioRepository(sessao_banco).garantir(
        usuario.id, usuario.nome, usuario.perfil.value, usuario.email
    )

    async def sem_injecao(texto):
        return ResultadoInjection(suspeita=False, confianca=0.0, motivo="limpo")

    async def sem_abuso(texto):
        return ResultadoAbuso(abusiva=False, confianca=0.0)

    async def classificar(texto):
        return ResultadoIntencao("consultar_status_projeto", 0.94)

    async def saida_limpa(texto, intencao_id):
        return ResultadoSaida(suspeita=False, confianca=0.0, motivo="limpo")

    monkeypatch.setattr(orq.injecao_regras, "contem_padrao_suspeito", lambda texto: False)
    monkeypatch.setattr(orq.injecao_classificador, "classificar", sem_injecao)
    monkeypatch.setattr(orq.abuso_classificador, "classificar", sem_abuso)
    monkeypatch.setattr(orq.intencao_classificador, "classificar", classificar)
    monkeypatch.setattr(orq.intencao_classificador, "limiar_de", lambda intencao_id: None)
    monkeypatch.setattr(orq.guarda_saida, "verificar", saida_limpa)

    interacoes = InteracaoRepository(sessao_banco)
    pipeline = Orquestrador(
        copilot=CopilotFalso(),
        interacoes=interacoes,
        conversas=ConversaRepository(sessao_banco),
    )
    prompt = "Qual o status do Projeto Verde?"
    resposta = await pipeline.processar(
        ChatRequest(mensagem=prompt, canal=Canal.VOZ), usuario, canal=Canal.VOZ
    )
    gravadas = await interacoes.listar_por_conversa(resposta.conversa_id, usuario.id)

    assert len(gravadas) == 1
    interacao = gravadas[0]
    assert interacao.prompt == prompt
    assert interacao.resposta == "O Projeto Verde está com 60% de avanço."
    assert interacao.intencao_id == "consultar_status_projeto"
    assert interacao.confianca_intencao == pytest.approx(0.94)
    assert interacao.desfecho is Desfecho.ENCAMINHADA
    assert interacao.canal is Canal.VOZ
    assert interacao.usuario_id == usuario.id
    assert interacao.criada_em <= datetime.now(UTC)
    assert interacao.latencia_ms >= 0
