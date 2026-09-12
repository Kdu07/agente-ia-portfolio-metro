"""Testes do cliente de Fast Transcription sem acessar o Azure real."""

import json

import httpx
import pytest

from app.config import settings
from app.voz.transcricao import ErroTranscricao, transcrever_arquivo


def _configurar(monkeypatch) -> None:
    monkeypatch.setattr(settings, "speech_key", "chave-de-teste")
    monkeypatch.setattr(settings, "speech_endpoint", "https://speech.example.com")
    monkeypatch.setattr(settings, "speech_idioma", "pt-BR")
    monkeypatch.setattr(settings, "speech_api_version", "2025-10-15")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("nome", "tipo"),
    [("fala.wav", "audio/wav"), ("fala.webm", "audio/webm")],
)
async def test_transcreve_formatos_aceitos(tmp_path, monkeypatch, nome, tipo) -> None:
    _configurar(monkeypatch)
    arquivo = tmp_path / nome
    arquivo.write_bytes(b"audio-falso")

    async def responder(request: httpx.Request) -> httpx.Response:
        corpo = await request.aread()
        assert request.url.params["api-version"] == "2025-10-15"
        assert request.headers["Ocp-Apim-Subscription-Key"] == "chave-de-teste"
        assert tipo.encode() in corpo
        return httpx.Response(
            200,
            json={
                "durationMilliseconds": 1250,
                "combinedPhrases": [{"text": "Qual o status do projeto?"}],
                "phrases": [{"text": "Qual o status do projeto?", "confidence": 0.94}],
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(responder)) as cliente:
        resultado = await transcrever_arquivo(arquivo, cliente=cliente)

    assert resultado.texto == "Qual o status do projeto?"
    assert resultado.idioma == "pt-BR"
    assert resultado.confianca == pytest.approx(0.94)
    assert resultado.duracao_segundos == pytest.approx(1.25)
    assert resultado.latencia_ms >= 0


@pytest.mark.asyncio
async def test_une_segmentos_e_calcula_confianca_media(tmp_path, monkeypatch) -> None:
    _configurar(monkeypatch)
    arquivo = tmp_path / "fala.mp3"
    arquivo.write_bytes(b"ID3-audio-falso")
    resposta = {
        "phrases": [
            {"text": "Primeira parte.", "confidence": 0.8},
            {"text": "Segunda parte.", "confidence": 1.0},
        ]
    }
    transporte = httpx.MockTransport(lambda _: httpx.Response(200, json=resposta))
    async with httpx.AsyncClient(transport=transporte) as cliente:
        resultado = await transcrever_arquivo(arquivo, cliente=cliente)
    assert resultado.texto == "Primeira parte. Segunda parte."
    assert resultado.confianca == pytest.approx(0.9)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status", "codigo"),
    [(400, "AUDIO_ILEGIVEL"), (429, "COTA_EXCEDIDA"), (503, "SERVICO_INDISPONIVEL")],
)
async def test_traduz_erros_do_provedor(tmp_path, monkeypatch, status, codigo) -> None:
    _configurar(monkeypatch)
    arquivo = tmp_path / "fala.ogg"
    arquivo.write_bytes(b"OggS-audio-falso")
    transporte = httpx.MockTransport(lambda _: httpx.Response(status))
    async with httpx.AsyncClient(transport=transporte) as cliente:
        with pytest.raises(ErroTranscricao) as erro:
            await transcrever_arquivo(arquivo, cliente=cliente)
    assert erro.value.codigo == codigo
    assert erro.value.status_provedor == status


@pytest.mark.asyncio
async def test_informa_quando_nao_ha_fala(tmp_path, monkeypatch) -> None:
    _configurar(monkeypatch)
    arquivo = tmp_path / "silencio.wav"
    arquivo.write_bytes(b"RIFF-audio-falso")
    transporte = httpx.MockTransport(lambda _: httpx.Response(200, json={"phrases": []}))
    async with httpx.AsyncClient(transport=transporte) as cliente:
        with pytest.raises(ErroTranscricao, match="Nenhuma fala") as erro:
            await transcrever_arquivo(arquivo, cliente=cliente)
    assert erro.value.codigo == "FALA_NAO_RECONHECIDA"


@pytest.mark.asyncio
async def test_envia_lista_de_frases_sem_duplicatas(tmp_path, monkeypatch) -> None:
    _configurar(monkeypatch)
    arquivo = tmp_path / "fala.m4a"
    arquivo.write_bytes(b"audio-falso")

    async def responder(request: httpx.Request) -> httpx.Response:
        corpo = (await request.aread()).decode(errors="ignore")
        inicio = corpo.index('{"locales"')
        fim = corpo.index("\r\n", inicio)
        definicao = json.loads(corpo[inicio:fim])
        assert definicao["phraseList"]["phrases"] == ["Linha 1-Azul", "Projeto Verde"]
        return httpx.Response(200, json={"combinedPhrases": [{"text": "Projeto Verde"}]})

    async with httpx.AsyncClient(transport=httpx.MockTransport(responder)) as cliente:
        await transcrever_arquivo(
            arquivo,
            frases=["Linha 1-Azul", "Projeto Verde", "Linha 1-Azul", " "],
            cliente=cliente,
        )
