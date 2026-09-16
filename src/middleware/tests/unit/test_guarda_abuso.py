"""Testes da guarda de abuso (guardas.abuso.classificador).

O Content Safety é dublado por `httpx.MockTransport`. O que estes testes
fixam, além do contrato da chamada, é a assimetria em relação à guarda de
injeção: aqui a queda do serviço falha ABERTO, e as políticas
corporativas continuam valendo quando ele não responde.
"""

import json
from collections.abc import Callable

import httpx
import pytest

from app.config import settings
from app.pipeline.guardas import content_safety
from app.pipeline.guardas.abuso import classificador, politicas
from app.pipeline.guardas.abuso.politicas import Politica, ViolacaoPolitica

LIMPA = "Qual o avanço físico do projeto PRJ-2024-018?"

VIOLACAO = ViolacaoPolitica(
    politica=Politica.DADO_PESSOAL_DE_TERCEIRO, confianca=0.8, trecho="salário do fulano"
)


@pytest.fixture
def sem_content_safety(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "content_safety_endpoint", "")
    monkeypatch.setattr(settings, "content_safety_key", "")


@pytest.fixture
def com_content_safety(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        settings, "content_safety_endpoint", "https://cs-teste.cognitiveservices.azure.com/"
    )
    monkeypatch.setattr(settings, "content_safety_key", "chave-de-teste")
    monkeypatch.setattr(settings, "content_safety_limiar_severidade", 2)


@pytest.fixture
def com_violacao(monkeypatch: pytest.MonkeyPatch) -> None:
    """Política corporativa acusando, como quando os enunciados existirem."""
    monkeypatch.setattr(politicas, "avaliar", lambda _: [VIOLACAO])


def servico(
    responder: Callable[[httpx.Request], httpx.Response],
) -> tuple[httpx.MockTransport, list[httpx.Request]]:
    chamadas: list[httpx.Request] = []

    def manipular(request: httpx.Request) -> httpx.Response:
        chamadas.append(request)
        return responder(request)

    return httpx.MockTransport(manipular), chamadas


def veredito(**severidades: int) -> Callable[[httpx.Request], httpx.Response]:
    """Resposta do serviço com a severidade de cada categoria."""
    return lambda _: httpx.Response(
        200,
        json={
            "categoriesAnalysis": [
                {"category": categoria, "severity": severidades.get(categoria, 0)}
                for categoria in classificador.CATEGORIAS
            ]
        },
    )


# --- Categorias do Content Safety ------------------------------------------


@pytest.mark.usefixtures("com_content_safety")
async def test_categoria_acima_do_limiar_recusa() -> None:
    transporte, _ = servico(veredito(Hate=4))

    resultado = await classificador.classificar("mensagem ofensiva", transporte=transporte)

    assert resultado.abusiva
    assert resultado.categoria == "Hate"
    assert resultado.motivo == "Hate"
    assert resultado.confianca == pytest.approx(4 / 6)


@pytest.mark.usefixtures("com_content_safety")
async def test_categoria_mais_severa_prevalece() -> None:
    """Com duas acusando, o registro mostra a mais grave."""
    transporte, _ = servico(veredito(Hate=2, Violence=6))

    resultado = await classificador.classificar("mensagem ofensiva", transporte=transporte)

    assert resultado.categoria == "Violence"


@pytest.mark.usefixtures("com_content_safety")
async def test_abaixo_do_limiar_passa() -> None:
    transporte, chamadas = servico(veredito(Violence=1))

    resultado = await classificador.classificar(LIMPA, transporte=transporte)

    assert not resultado.abusiva
    assert resultado.categoria is None
    assert resultado.motivo == "nao_especificado"
    [chamada] = chamadas
    assert chamada.url.path == "/contentsafety/text:analyze"
    assert chamada.url.params["api-version"] == content_safety.API_VERSION
    assert chamada.headers["Ocp-Apim-Subscription-Key"] == "chave-de-teste"
    corpo = json.loads(chamada.content)
    assert corpo["text"] == LIMPA
    assert corpo["categories"] == list(classificador.CATEGORIAS)
    assert corpo["outputType"] == "FourSeverityLevels"


@pytest.mark.usefixtures("com_content_safety")
@pytest.mark.parametrize("texto", ["", "   "])
async def test_mensagem_vazia_nao_chama_o_servico(texto: str) -> None:
    transporte, chamadas = servico(veredito(Hate=6))

    resultado = await classificador.classificar(texto, transporte=transporte)

    assert not resultado.abusiva
    assert chamadas == []


# --- Falha aberta ----------------------------------------------------------


def _tempo_esgotado(request: httpx.Request) -> httpx.Response:
    raise httpx.ReadTimeout("tempo esgotado", request=request)


@pytest.mark.usefixtures("com_content_safety")
@pytest.mark.parametrize(
    "responder",
    [
        lambda _: httpx.Response(503),
        lambda _: httpx.Response(200, json={}),
        lambda _: httpx.Response(200, text="não é json"),
        _tempo_esgotado,
    ],
    ids=["503", "sem-campo", "nao-json", "timeout"],
)
async def test_falha_do_servico_deixa_passar(responder) -> None:
    """Falha ABERTO, ao contrário da injeção: a mensagem já passou por ela."""
    transporte, _ = servico(responder)

    resultado = await classificador.classificar(LIMPA, transporte=transporte)

    assert not resultado.abusiva
    assert resultado.categoria is None


def _corpo(analises: object) -> Callable[[httpx.Request], httpx.Response]:
    return lambda _: httpx.Response(200, json={"categoriesAnalysis": analises})


@pytest.mark.usefixtures("com_content_safety")
@pytest.mark.parametrize(
    "analises",
    [
        [{"category": "Hate", "severity": "alta"}],
        [{"category": "Hate", "severity": {}}],
        [{"category": None, "severity": 6}],
        [{"severity": 6}],
        ["Hate"],
    ],
    ids=["severidade-texto", "severidade-objeto", "categoria-nula", "sem-categoria", "nao-objeto"],
)
async def test_contrato_malformado_deixa_passar(analises: object) -> None:
    """Corpo ilegível é indisponibilidade, não exceção: a guarda falha ABERTO.

    Um `ValueError` escapando da coerção subiria até o orquestrador, que
    não captura guardas, e viraria 500 no `/chat`.
    """
    transporte, _ = servico(_corpo(analises))

    resultado = await classificador.classificar(LIMPA, transporte=transporte)

    assert not resultado.abusiva
    assert resultado.categoria is None


@pytest.mark.usefixtures("com_content_safety", "com_violacao")
async def test_politica_vale_com_contrato_malformado() -> None:
    """A camada corporativa sobrevive ao corpo ilegível, como sobrevive à queda."""
    transporte, _ = servico(_corpo([{"category": "Hate", "severity": "alta"}]))

    resultado = await classificador.classificar("dados do colega", transporte=transporte)

    assert resultado.abusiva
    assert resultado.categoria is None
    assert resultado.violacoes == [VIOLACAO]


@pytest.mark.usefixtures("sem_content_safety")
async def test_sem_credencial_nao_chama_o_servico() -> None:
    transporte, chamadas = servico(veredito(Hate=6))

    resultado = await classificador.classificar(LIMPA, transporte=transporte)

    assert not resultado.abusiva
    assert chamadas == []


# --- Políticas corporativas ------------------------------------------------


async def test_politicas_sem_enunciados_nao_acusam() -> None:
    """Enquanto o parceiro não definir os enunciados, a camada é neutra."""
    assert politicas.avaliar("qualquer coisa") == []


@pytest.mark.usefixtures("sem_content_safety", "com_violacao")
async def test_politica_recusa_sem_o_servico() -> None:
    """A camada corporativa é local: não depende do Content Safety."""
    transporte, chamadas = servico(veredito())

    resultado = await classificador.classificar("dados do colega", transporte=transporte)

    assert resultado.abusiva
    assert resultado.violacoes == [VIOLACAO]
    assert resultado.motivo == "dado_pessoal_de_terceiro"
    assert resultado.confianca == 0.8
    assert chamadas == []


@pytest.mark.usefixtures("com_content_safety", "com_violacao")
async def test_politica_e_categoria_aparecem_juntas() -> None:
    transporte, _ = servico(veredito(Hate=6))

    resultado = await classificador.classificar("dados do colega", transporte=transporte)

    assert resultado.abusiva
    assert resultado.motivo == "Hate,dado_pessoal_de_terceiro"
    assert resultado.confianca == 1.0


@pytest.mark.usefixtures("com_content_safety", "com_violacao")
async def test_politica_vale_com_o_servico_fora() -> None:
    transporte, _ = servico(_tempo_esgotado)

    resultado = await classificador.classificar("dados do colega", transporte=transporte)

    assert resultado.abusiva
    assert resultado.categoria is None
    assert resultado.violacoes == [VIOLACAO]
