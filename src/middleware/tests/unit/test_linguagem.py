"""Testes da porta do modelo de linguagem e dos adaptadores Gemini e OpenRouter (rag.linguagem).

O cliente do SDK e a rede do OpenRouter são dublados: nenhuma chamada
sai da máquina, nenhuma chave é necessária. O que se afirma é o que o adaptador decide por
conta própria — por qual canal cada parte do prompt viaja, o que é
repetido e o que não é, e que ausência de resposta é erro, nunca texto
vazio. O contrato com o serviço real fica em
`tests/integration/externos/test_gemini_real.py`.
"""

import asyncio
import json
from types import SimpleNamespace

import httpx
import pytest

from app.config import settings
from app.rag.linguagem.base import ErroGeracao, ModeloLinguagem
from app.rag.linguagem.fabrica import obter_modelo_linguagem
from app.rag.linguagem.gemini import ModeloGemini
from app.rag.linguagem.openrouter import ModeloOpenRouter

INSTRUCOES = "regras do sistema"
CONTEUDO = "<documentos>...</documentos>\n<pergunta>custo?</pergunta>"


class ErroApi(Exception):
    """Erro do SDK como ele se apresenta: com o código HTTP em `.code`."""

    def __init__(self, code: int, mensagem: str = "erro") -> None:
        super().__init__(mensagem)
        self.code = code


class ClienteFalso:
    """Imita `genai.Client`: só `cliente.aio.models.generate_content`.

    Cada item de `roteiro` é o desfecho de uma chamada: texto (resposta),
    `None` (resposta sem texto), exceção (levantada) ou um número de
    segundos a dormir antes de responder (para o teto de tempo).
    """

    def __init__(self, *roteiro) -> None:
        self.chamadas: list[dict] = []
        self._roteiro = list(roteiro)
        self.aio = SimpleNamespace(models=self)

    async def generate_content(self, **kwargs):
        self.chamadas.append(kwargs)
        desfecho = self._roteiro.pop(0)
        if isinstance(desfecho, Exception):
            raise desfecho
        if isinstance(desfecho, float):
            await asyncio.sleep(desfecho)
            return SimpleNamespace(text="tarde demais")
        return SimpleNamespace(text=desfecho)


class Relogio:
    """Substitui `asyncio.sleep` entre tentativas e guarda as esperas."""

    def __init__(self) -> None:
        self.esperas: list[float] = []

    async def __call__(self, segundos: float) -> None:
        self.esperas.append(segundos)


def modelo(cliente: ClienteFalso, relogio: Relogio | None = None, **kwargs) -> ModeloGemini:
    return ModeloGemini(
        cliente, "gemini-teste", timeout=5.0, dormir=relogio or Relogio(), **kwargs
    )


async def gerar(adaptador: ModeloGemini) -> str:
    return await adaptador.gerar(instrucoes=INSTRUCOES, conteudo=CONTEUDO)


# --- Canais -----------------------------------------------------------------


async def test_instrucao_e_conteudo_vao_por_canais_distintos() -> None:
    """A fronteira da seção 4.4 materializada no protocolo do provedor."""
    cliente = ClienteFalso("resposta [1]")

    await gerar(modelo(cliente))

    chamada = cliente.chamadas[0]
    assert chamada["model"] == "gemini-teste"
    assert chamada["config"]["system_instruction"] == INSTRUCOES
    assert chamada["contents"] == CONTEUDO
    assert INSTRUCOES not in chamada["contents"]


async def test_devolve_o_texto_do_modelo() -> None:
    assert await gerar(modelo(ClienteFalso("resposta [1]"))) == "resposta [1]"


def test_nome_identifica_provedor_e_modelo() -> None:
    assert modelo(ClienteFalso()).nome == "gemini/gemini-teste"


def test_adaptador_implementa_a_porta() -> None:
    assert isinstance(modelo(ClienteFalso()), ModeloLinguagem)


# --- Novas tentativas -------------------------------------------------------


async def test_cota_esgotada_e_repetida_com_espera_crescente() -> None:
    """Risco da seção 8: sem espera, a bancada falha pela metade."""
    cliente, relogio = ClienteFalso(ErroApi(429), ErroApi(503), "resposta [1]"), Relogio()

    texto = await gerar(modelo(cliente, relogio))

    assert texto == "resposta [1]"
    assert len(cliente.chamadas) == 3
    assert relogio.esperas == [2.0, 4.0]


async def test_erro_do_pedido_nao_e_repetido() -> None:
    """Chave inválida não passa sozinha; repetir só atrasaria o erro."""
    cliente, relogio = ClienteFalso(ErroApi(400)), Relogio()

    with pytest.raises(ErroGeracao, match="400"):
        await gerar(modelo(cliente, relogio))

    assert len(cliente.chamadas) == 1
    assert relogio.esperas == []


async def test_tentativas_esgotadas_levantam_erro_de_geracao() -> None:
    cliente = ClienteFalso(ErroApi(429), ErroApi(429), ErroApi(429))

    with pytest.raises(ErroGeracao, match="3 tentativas"):
        await gerar(modelo(cliente, tentativas=3))

    assert len(cliente.chamadas) == 3


async def test_tempo_esgotado_e_transitorio() -> None:
    cliente = ClienteFalso(1.0, "resposta [1]")
    adaptador = ModeloGemini(cliente, "gemini-teste", timeout=0.01, dormir=Relogio())

    assert await gerar(adaptador) == "resposta [1]"
    assert len(cliente.chamadas) == 2


async def test_erro_nao_carrega_o_conteudo_enviado() -> None:
    """O traço do provedor pode ecoar o payload; o erro que sobe não."""
    cliente = ClienteFalso(ErroApi(400, mensagem=f"invalid request: {CONTEUDO}"))

    with pytest.raises(ErroGeracao) as capturado:
        await gerar(modelo(cliente))

    assert CONTEUDO not in str(capturado.value)
    assert "custo?" not in str(capturado.value)


# --- Resposta vazia ---------------------------------------------------------


@pytest.mark.parametrize("texto", [None, "", "   \n"])
async def test_resposta_sem_texto_e_erro_e_nao_string_vazia(texto) -> None:
    """Bloqueio do provedor lido como texto vazio viraria "resposta sem
    citação" — uma recusa que parece legítima escondendo uma falha."""
    with pytest.raises(ErroGeracao, match="vazia"):
        await gerar(modelo(ClienteFalso(texto)))


# --- Fábrica ----------------------------------------------------------------


def test_fabrica_recusa_backend_desconhecido(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "llm_backend", "gpt")

    with pytest.raises(ValueError, match="gpt"):
        obter_modelo_linguagem()


def test_fabrica_exige_a_chave_do_gemini(monkeypatch: pytest.MonkeyPatch) -> None:
    """Falha na montagem, nomeando a variável, e não na primeira pergunta."""
    monkeypatch.setattr(settings, "llm_backend", " Gemini ")  # tolera caixa e espaço
    monkeypatch.setattr(settings, "gemini_api_key", "")

    with pytest.raises(RuntimeError, match="gemini_api_key"):
        obter_modelo_linguagem()


def test_fabrica_seleciona_o_openrouter(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "llm_backend", "openrouter")
    monkeypatch.setattr(settings, "openrouter_api_key", "chave-teste")
    monkeypatch.setattr(settings, "openrouter_modelo", "google/modelo-teste")

    adaptador = obter_modelo_linguagem()

    assert isinstance(adaptador, ModeloOpenRouter)
    assert adaptador.nome == "openrouter/google/modelo-teste"


def test_fabrica_exige_a_chave_do_openrouter(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "llm_backend", "openrouter")
    monkeypatch.setattr(settings, "openrouter_api_key", "")

    with pytest.raises(RuntimeError, match="openrouter_api_key"):
        obter_modelo_linguagem()


# --- OpenRouter -------------------------------------------------------------


def rede(*desfechos) -> tuple[httpx.MockTransport, list[httpx.Request]]:
    """Transporte dublado: cada desfecho é a resposta de um pedido, ou a exceção dele."""
    pedidos: list[httpx.Request] = []
    fila = list(desfechos)

    def tratar(pedido: httpx.Request) -> httpx.Response:
        pedidos.append(pedido)
        desfecho = fila.pop(0)
        if isinstance(desfecho, Exception):
            raise desfecho
        return desfecho

    return httpx.MockTransport(tratar), pedidos


def escolha(texto) -> httpx.Response:
    return httpx.Response(200, json={"choices": [{"message": {"content": texto}}]})


def openrouter(transporte, relogio: Relogio | None = None, **kwargs) -> ModeloOpenRouter:
    return ModeloOpenRouter(
        "chave-teste",
        "google/modelo-teste",
        timeout=5.0,
        transporte=transporte,
        dormir=relogio or Relogio(),
        **kwargs,
    )


async def gerar_openrouter(adaptador: ModeloOpenRouter) -> str:
    return await adaptador.gerar(instrucoes=INSTRUCOES, conteudo=CONTEUDO)


async def test_openrouter_separa_instrucao_e_conteudo() -> None:
    """A mesma fronteira da seção 4.4, nas mensagens `system` e `user`."""
    transporte, pedidos = rede(escolha("resposta [1]"))

    assert await gerar_openrouter(openrouter(transporte)) == "resposta [1]"

    corpo = json.loads(pedidos[0].content)
    assert corpo["model"] == "google/modelo-teste"
    assert corpo["messages"] == [
        {"role": "system", "content": INSTRUCOES},
        {"role": "user", "content": CONTEUDO},
    ]
    assert pedidos[0].headers["Authorization"] == "Bearer chave-teste"


def test_openrouter_implementa_a_porta() -> None:
    assert isinstance(openrouter(None), ModeloLinguagem)


async def test_openrouter_repete_o_transitorio_com_espera_crescente() -> None:
    transporte, pedidos = rede(
        httpx.Response(429), httpx.ConnectTimeout("lento"), escolha("resposta [1]")
    )
    relogio = Relogio()

    assert await gerar_openrouter(openrouter(transporte, relogio)) == "resposta [1]"
    assert len(pedidos) == 3
    assert relogio.esperas == [2.0, 4.0]


async def test_openrouter_le_o_erro_que_vem_com_status_200() -> None:
    """O provedor por trás do OpenRouter falhou depois de aceito o pedido."""
    transporte, pedidos = rede(
        httpx.Response(200, json={"error": {"code": 502, "message": "provedor caiu"}}),
        escolha("resposta [1]"),
    )

    assert await gerar_openrouter(openrouter(transporte)) == "resposta [1]"
    assert len(pedidos) == 2


async def test_openrouter_nao_repete_erro_do_pedido_nem_ecoa_o_conteudo() -> None:
    transporte, pedidos = rede(
        httpx.Response(400, json={"error": {"code": 400, "message": f"invalid: {CONTEUDO}"}})
    )

    with pytest.raises(ErroGeracao, match="400") as capturado:
        await gerar_openrouter(openrouter(transporte))

    assert len(pedidos) == 1
    assert "custo?" not in str(capturado.value)


async def test_openrouter_tentativas_esgotadas_levantam_erro_de_geracao() -> None:
    transporte, _ = rede(httpx.Response(503), httpx.Response(503))

    with pytest.raises(ErroGeracao, match="2 tentativas"):
        await gerar_openrouter(openrouter(transporte, tentativas=2))


@pytest.mark.parametrize(
    "resposta",
    [
        escolha(None),
        escolha("   \n"),
        httpx.Response(200, json={"choices": []}),
        httpx.Response(200, text="não é json"),
    ],
)
async def test_openrouter_resposta_sem_texto_e_erro(resposta: httpx.Response) -> None:
    transporte, _ = rede(resposta)

    with pytest.raises(ErroGeracao, match="vazia"):
        await gerar_openrouter(openrouter(transporte))
