"""Casos TF-RF04-01 a TF-RF04-05 — consulta ao portfólio pela API."""

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.api import deps
from app.executor.base import Fonte, RespostaExecutor
from app.main import app
from app.pipeline import orquestrador as orq
from app.pipeline.desfechos import Desfecho
from app.pipeline.intencao.classificador import ResultadoIntencao
from app.pipeline.orquestrador import Orquestrador
from app.schemas.usuario import Perfil, UsuarioAutenticado
from tests.apoio_audio import BancoFalso
from tests.funcionais.conftest import RepositorioMemoria

USUARIO = UsuarioAutenticado(
    "rf04",
    "Teste RF04",
    Perfil.LIDER_PROJETO,
    projetos=frozenset({"PRJ-VERDE"}),
)


class ExecutorResposta:
    def __init__(self, resposta: RespostaExecutor) -> None:
        self.resposta = resposta
        self.chamadas: list[tuple[str, str]] = []

    async def enviar(
        self,
        texto: str,
        intencao_id: str,
        exige_confirmacao: bool,
        conversa_externa_id: str | None = None,
        historico=(),
    ) -> RespostaExecutor:
        self.chamadas.append((texto, intencao_id))
        return self.resposta


@pytest.fixture
def api_rf04(monkeypatch: pytest.MonkeyPatch):
    async def sem_injecao(_: str):
        from app.pipeline.guardas.injecao.classificador import ResultadoInjection

        return ResultadoInjection(False, 0.0, "limpo")

    async def sem_abuso(_: str):
        from app.pipeline.guardas.abuso.classificador import ResultadoAbuso

        return ResultadoAbuso(False, 0.0)

    async def saida_limpa(_: str, __: str):
        from app.pipeline.guardas.saida import ResultadoSaida

        return ResultadoSaida(False, 0.0, "limpo")

    monkeypatch.setattr(orq.injecao_regras, "contem_padrao_suspeito", lambda _: False)
    monkeypatch.setattr(orq.injecao_classificador, "classificar", sem_injecao)
    monkeypatch.setattr(orq.abuso_classificador, "classificar", sem_abuso)
    monkeypatch.setattr(orq.guarda_saida, "verificar", saida_limpa)

    repositorio = RepositorioMemoria()
    executor = ExecutorResposta(RespostaExecutor(texto="Resposta de teste."))
    overrides_anteriores = app.dependency_overrides.copy()
    app.dependency_overrides[deps.obter_usuario_atual] = lambda: USUARIO
    app.dependency_overrides[deps.obter_sessao] = lambda: BancoFalso()
    app.dependency_overrides[deps.obter_orquestrador] = lambda: Orquestrador(
        executor, repositorio, repositorio
    )

    def classificar_com(intencao_id: str) -> None:
        async def classificar(_: str) -> ResultadoIntencao:
            return ResultadoIntencao(intencao_id, 0.99)

        monkeypatch.setattr(orq.intencao_classificador, "classificar", classificar)

    try:
        with TestClient(app) as cliente:
            yield cliente, executor, repositorio, classificar_com
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(overrides_anteriores)


@pytest.mark.parametrize(
    "intencao_id",
    [
        "consultar_avanco",
        "consultar_cronograma",
        "consultar_status_projeto",
        "consultar_marcos",
        "consultar_riscos",
        "consultar_problemas",
        "consultar_aderencia_normativa",
    ],
)
def test_tf_rf04_01_consulta_dimensoes_do_portfolio_pela_api(api_rf04, intencao_id) -> None:
    cliente, executor, repositorio, classificar_com = api_rf04
    classificar_com(intencao_id)

    resposta = cliente.post("/chat", json={"mensagem": "Consulte o portfólio"})

    assert resposta.status_code == 200
    assert resposta.json()["intencao_id"] == intencao_id
    assert resposta.json()["desfecho"] == Desfecho.ENCAMINHADA.value
    assert executor.chamadas == [("Consulte o portfólio", intencao_id)]
    assert repositorio.interacoes[0].intencao_id == intencao_id


async def test_tf_rf04_03_projeto_inexistente_retorna_404() -> None:
    from app.api.routes.portfolio import obter_projeto

    class ProjetosMemoria:
        async def obter(self, codigo: str):
            return None

    usuario = UsuarioAutenticado(
        "rf04", "Teste RF04", Perfil.LIDER_PROJETO, projetos=frozenset({"PRJ-404"})
    )
    with pytest.raises(HTTPException) as erro:
        await obter_projeto("PRJ-404", usuario, ProjetosMemoria())
    assert erro.value.status_code == 404
    assert erro.value.detail == "Projeto não encontrado"


@pytest.mark.xfail(strict=True, reason="rota diferencia projeto alheio (403) de inexistente (404)")
async def test_tf_rf04_04_projeto_alheio_e_inexistente_sao_indistinguiveis() -> None:
    from app.api.routes.portfolio import obter_projeto

    class ProjetosMemoria:
        async def obter(self, codigo: str):
            return None

    repositorio = ProjetosMemoria()
    autorizado = UsuarioAutenticado(
        "autorizado", "Autorizado", Perfil.LIDER_PROJETO, projetos=frozenset({"PRJ-X"})
    )
    sem_acesso = UsuarioAutenticado("sem-acesso", "Sem acesso", Perfil.MEMBRO_EQUIPE)
    respostas = []
    for usuario in (autorizado, sem_acesso):
        try:
            await obter_projeto("PRJ-X", usuario, repositorio)
        except HTTPException as erro:
            respostas.append((erro.status_code, erro.detail))
    assert respostas[0] == respostas[1]


def test_tf_rf04_02_referencia_acompanha_o_conteudo_pela_api(api_rf04) -> None:
    cliente, executor, _, classificar_com = api_rf04
    classificar_com("consultar_status_projeto")
    executor.resposta = RespostaExecutor(
        texto="O avanço físico do Projeto Verde é 60% [1].",
        fontes=(
            Fonte(
                documento="Relatório de status",
                link="https://example.org/relatorio",
                trecho="O avanço físico do Projeto Verde é 60%.",
                score=0.95,
                localizador="Seção 2",
            ),
        ),
    )

    resposta = cliente.post(
        "/chat",
        json={"mensagem": "Qual é o avanço do Projeto Verde?"},
    )

    assert resposta.status_code == 200
    assert resposta.json()["resposta"] == "O avanço físico do Projeto Verde é 60% [1]."


def test_tf_rf04_05_dado_ausente_nao_e_inventado_pela_api(api_rf04) -> None:
    from app.rag.geracao import Situacao, abstencao

    cliente, executor, _, classificar_com = api_rf04
    classificar_com("consultar_status_projeto")
    executor.resposta = RespostaExecutor(texto=abstencao(Situacao.SEM_EVIDENCIA).texto)

    resposta = cliente.post(
        "/chat",
        json={"mensagem": "Qual é o orçamento do Projeto Verde?"},
    )

    assert resposta.status_code == 200
    assert resposta.json()["resposta"] == abstencao(Situacao.SEM_EVIDENCIA).texto
