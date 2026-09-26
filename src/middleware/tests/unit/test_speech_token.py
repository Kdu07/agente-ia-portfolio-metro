"""Emissão do token efêmero do Azure Speech sem acessar o Azure real."""

import httpx
import pytest

from app.config import settings
from app.voz.speech import (
    VALIDADE_SEGUNDOS,
    ErroConfiguracaoSpeech,
    ErroTokenSpeech,
    emitir_token,
)

CHAVE = "chave-de-teste-que-nao-pode-vazar"


@pytest.fixture(autouse=True)
def configurar(monkeypatch):
    monkeypatch.setattr(settings, "speech_key", CHAVE)
    monkeypatch.setattr(settings, "speech_region", "brazilsouth")
    monkeypatch.setattr(settings, "speech_endpoint", "")
    monkeypatch.setattr(settings, "speech_idioma", "pt-BR")


def cliente(responder) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(responder))


async def test_emite_token_pelo_endpoint_regional_com_a_chave_so_no_cabecalho():
    pedidos: list[httpx.Request] = []

    def responder(pedido: httpx.Request) -> httpx.Response:
        pedidos.append(pedido)
        return httpx.Response(200, text="eyJ.cabecalho.assinatura\n")

    async with cliente(responder) as c:
        emitido = await emitir_token(cliente=c)

    assert (emitido.token, emitido.regiao, emitido.idioma) == (
        "eyJ.cabecalho.assinatura",
        "brazilsouth",
        "pt-BR",
    )
    assert emitido.expira_em_segundos == VALIDADE_SEGUNDOS
    [pedido] = pedidos
    assert pedido.method == "POST"
    assert str(pedido.url) == "https://brazilsouth.api.cognitive.microsoft.com/sts/v1.0/issueToken"
    assert pedido.headers["Ocp-Apim-Subscription-Key"] == CHAVE
    assert CHAVE not in str(pedido.url) and pedido.content == b""


async def test_dominio_proprio_emite_pelo_proprio_dominio(monkeypatch):
    monkeypatch.setattr(
        settings, "speech_endpoint", "https://prata-voz.cognitiveservices.azure.com/"
    )
    urls: list[str] = []

    def responder(pedido: httpx.Request) -> httpx.Response:
        urls.append(str(pedido.url))
        return httpx.Response(200, text="token")

    async with cliente(responder) as c:
        await emitir_token(cliente=c)

    assert urls == ["https://prata-voz.cognitiveservices.azure.com/sts/v1.0/issueToken"]


@pytest.mark.parametrize("status", [401, 403, 429, 500])
async def test_recusa_do_servico_nao_repassa_o_corpo(status):
    # O corpo de erro do provedor pode ecoar dados do pedido.
    async with cliente(lambda _: httpx.Response(status, text=f"chave {CHAVE} recusada")) as c:
        with pytest.raises(ErroTokenSpeech) as erro:
            await emitir_token(cliente=c)

    assert CHAVE not in str(erro.value)
    assert str(status) in str(erro.value)


async def test_falha_de_rede_vira_indisponibilidade():
    def responder(pedido: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("sem rede", request=pedido)

    async with cliente(responder) as c:
        with pytest.raises(ErroTokenSpeech):
            await emitir_token(cliente=c)


async def test_token_vazio_e_recusado():
    async with cliente(lambda _: httpx.Response(200, text="  ")) as c:
        with pytest.raises(ErroTokenSpeech):
            await emitir_token(cliente=c)


@pytest.mark.parametrize("campo", ["speech_key", "speech_region"])
async def test_sem_configuracao_nao_chama_o_servico(monkeypatch, campo):
    monkeypatch.setattr(settings, campo, " ")
    chamadas: list[httpx.Request] = []

    async with cliente(lambda p: chamadas.append(p) or httpx.Response(200, text="x")) as c:
        with pytest.raises(ErroConfiguracaoSpeech):
            await emitir_token(cliente=c)

    assert chamadas == []
