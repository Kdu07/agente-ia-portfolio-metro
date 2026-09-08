"""Conversao de arquivos de audio pela API Fast Transcription do Azure."""

import json
import time
from asyncio import to_thread
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from statistics import fmean

import httpx

from app.config import settings

_TIPOS_AUDIO = {
    ".aac": "audio/aac", ".flac": "audio/flac", ".m4a": "audio/mp4",
    ".mp3": "audio/mpeg", ".mp4": "audio/mp4", ".ogg": "audio/ogg",
    ".wav": "audio/wav", ".webm": "audio/webm",
}


@dataclass(frozen=True)
class ResultadoTranscricao:
    """Resultado normalizado que sera consumido pelo pipeline de NLP."""

    texto: str
    idioma: str
    confianca: float | None
    duracao_segundos: float | None
    latencia_ms: int


class ErroTranscricao(RuntimeError):
    """Falha conhecida, segura para ser traduzida pela camada HTTP."""

    def __init__(self, codigo: str, mensagem: str, *, status_provedor: int | None = None) -> None:
        super().__init__(mensagem)
        self.codigo = codigo
        self.mensagem = mensagem
        self.status_provedor = status_provedor


def _validar_configuracao() -> tuple[str, str, str]:
    chave = settings.speech_key.strip()
    endpoint = settings.speech_endpoint.strip().rstrip("/")
    idioma = settings.speech_idioma.strip()
    if not chave:
        raise ErroTranscricao("CONFIGURACAO_INVALIDA", "SPEECH_KEY nao configurada")
    if not endpoint:
        raise ErroTranscricao("CONFIGURACAO_INVALIDA", "SPEECH_ENDPOINT nao configurado")
    if not idioma:
        raise ErroTranscricao("CONFIGURACAO_INVALIDA", "SPEECH_IDIOMA nao configurado")
    return chave, endpoint, idioma


def _extrair_resultado(payload: dict, idioma: str, latencia_ms: int) -> ResultadoTranscricao:
    combinadas = payload.get("combinedPhrases") or []
    frases = payload.get("phrases") or []
    textos = [item.get("text", "").strip() for item in combinadas]
    textos = [texto for texto in textos if texto]
    if not textos:
        textos = [item.get("text", "").strip() for item in frases]
        textos = [texto for texto in textos if texto]
    if not textos:
        raise ErroTranscricao("FALA_NAO_RECONHECIDA", "Nenhuma fala foi reconhecida no audio")
    confiancas = [item.get("confidence") for item in frases]
    confiancas = [float(valor) for valor in confiancas if isinstance(valor, (int, float))]
    duracao_ms = payload.get("durationMilliseconds")
    return ResultadoTranscricao(
        texto=" ".join(textos), idioma=idioma,
        confianca=fmean(confiancas) if confiancas else None,
        duracao_segundos=float(duracao_ms) / 1000 if isinstance(duracao_ms, (int, float)) else None,
        latencia_ms=latencia_ms,
    )


def _erro_do_provedor(resposta: httpx.Response) -> ErroTranscricao:
    status = resposta.status_code
    if status == 429:
        return ErroTranscricao("COTA_EXCEDIDA", "Limite temporario do servico de voz atingido", status_provedor=status)
    if status in {400, 404, 413, 415, 422}:
        return ErroTranscricao("AUDIO_ILEGIVEL", "O servico nao conseguiu processar o audio enviado", status_provedor=status)
    return ErroTranscricao("SERVICO_INDISPONIVEL", "Falha temporaria no servico de transcricao", status_provedor=status)


async def transcrever_arquivo(
    caminho: str | Path, *, idioma: str | None = None,
    frases: Iterable[str] = (), content_type: str | None = None,
    cliente: httpx.AsyncClient | None = None,
) -> ResultadoTranscricao:
    """Transcreve um arquivo validado usando o endpoint REST do Azure."""
    chave, endpoint, idioma_padrao = _validar_configuracao()
    idioma = (idioma or idioma_padrao).strip()
    arquivo = Path(caminho)
    if not arquivo.is_file():
        raise ErroTranscricao("ARQUIVO_NAO_ENCONTRADO", "Arquivo de audio nao encontrado")
    if arquivo.stat().st_size == 0:
        raise ErroTranscricao("AUDIO_ILEGIVEL", "O arquivo de audio esta vazio")
    tipo = content_type or _TIPOS_AUDIO.get(arquivo.suffix.lower())
    if not tipo:
        raise ErroTranscricao("FORMATO_NAO_SUPORTADO", "Formato de audio nao suportado")

    definicao: dict[str, object] = {"locales": [idioma]}
    frases_unicas = list(dict.fromkeys(frase.strip() for frase in frases if frase.strip()))
    if frases_unicas:
        definicao["phraseList"] = {"phrases": frases_unicas}

    inicio = time.perf_counter()
    proprio_cliente = cliente is None
    if proprio_cliente:
        cliente = httpx.AsyncClient(timeout=settings.speech_timeout_seconds)
    try:
        assert cliente is not None
        audio = await to_thread(arquivo.read_bytes)
        resposta = await cliente.post(
            f"{endpoint}/speechtotext/transcriptions:transcribe",
            params={"api-version": settings.speech_api_version},
            headers={"Ocp-Apim-Subscription-Key": chave},
            files={
                "audio": (arquivo.name, audio, tipo),
                "definition": (None, json.dumps(definicao), "application/json"),
            },
        )
    except (httpx.TimeoutException, httpx.NetworkError) as erro:
        raise ErroTranscricao("SERVICO_INDISPONIVEL", "Nao foi possivel acessar o servico de transcricao") from erro
    finally:
        if proprio_cliente and cliente is not None:
            await cliente.aclose()
    if resposta.status_code >= 400:
        raise _erro_do_provedor(resposta)
    try:
        payload = resposta.json()
    except ValueError as erro:
        raise ErroTranscricao("RESPOSTA_INVALIDA", "O servico devolveu uma resposta invalida") from erro
    latencia_ms = round((time.perf_counter() - inicio) * 1000)
    return _extrair_resultado(payload, idioma, latencia_ms)
