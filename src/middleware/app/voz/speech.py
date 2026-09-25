"""Configuração e acesso isolado ao Azure Speech.

A chave do recurso vive apenas aqui, no servidor. O navegador recebe um
token com validade curta (10 minutos, no padrão do serviço) e a região —
nunca a chave. Um token vazado expira sozinho; uma chave vazada precisa
ser rotacionada no tenant do parceiro.
"""

import argparse
import logging
from dataclasses import dataclass
from pathlib import Path

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

# Validade do token emitido pelo serviço. O frontend deve renovar antes
# de expirar, e não ao receber erro: uma renovação reativa interromperia
# a fala do usuário no meio.
VALIDADE_SEGUNDOS = 600


@dataclass(frozen=True)
class TokenVoz:
    """Credencial temporária entregue ao navegador."""

    token: str
    regiao: str
    expira_em_segundos: int = VALIDADE_SEGUNDOS
    idioma: str = "pt-BR"


@dataclass(frozen=True)
class ResultadoReconhecimento:
    """Texto reconhecido em um arquivo pelo smoke test do serviço."""

    texto: str
    idioma: str


class ErroConfiguracaoSpeech(RuntimeError):
    """Configuração local ausente ou inválida."""


class ErroReconhecimentoSpeech(RuntimeError):
    """O Azure Speech não produziu uma transcrição utilizável."""


class ErroTokenSpeech(RuntimeError):
    """O servidor não conseguiu emitir a credencial efêmera de voz."""

    def __init__(self, mensagem: str, *, cota_excedida: bool = False) -> None:
        super().__init__(mensagem)
        self.cota_excedida = cota_excedida


def reconhecer_arquivo_wav(
    caminho: str | Path,
    *,
    chave: str | None = None,
    regiao: str | None = None,
    idioma: str | None = None,
    _speechsdk=None,
) -> ResultadoReconhecimento:
    """Reconhece uma fala curta em WAV para validar a configuração.

    Esta função é deliberadamente isolada da API de upload. Ela constitui o
    smoke test da task de configuração do SDK; processamento de formatos
    comprimidos, persistência e execução assíncrona pertencem à integração
    subsequente.
    """
    chave = chave if chave is not None else settings.speech_key
    regiao = regiao if regiao is not None else settings.speech_region
    idioma = idioma if idioma is not None else settings.speech_idioma

    if not chave.strip():
        raise ErroConfiguracaoSpeech("SPEECH_KEY não configurada")
    if not regiao.strip():
        raise ErroConfiguracaoSpeech("SPEECH_REGION não configurada")
    if not idioma.strip():
        raise ErroConfiguracaoSpeech("SPEECH_IDIOMA não configurado")

    arquivo = Path(caminho)
    if arquivo.suffix.lower() != ".wav":
        raise ErroConfiguracaoSpeech("O teste isolado aceita apenas arquivo WAV")
    if not arquivo.is_file():
        raise ErroConfiguracaoSpeech(f"Arquivo WAV não encontrado: {arquivo}")

    if _speechsdk is None:
        import azure.cognitiveservices.speech as speechsdk
    else:
        speechsdk = _speechsdk

    speech_config = speechsdk.SpeechConfig(subscription=chave, region=regiao)
    speech_config.speech_recognition_language = idioma
    audio_config = speechsdk.audio.AudioConfig(filename=str(arquivo))
    reconhecedor = speechsdk.SpeechRecognizer(
        speech_config=speech_config,
        audio_config=audio_config,
    )
    resultado = reconhecedor.recognize_once_async().get()

    if resultado.reason == speechsdk.ResultReason.RecognizedSpeech and resultado.text.strip():
        return ResultadoReconhecimento(texto=resultado.text.strip(), idioma=idioma)
    if resultado.reason == speechsdk.ResultReason.NoMatch:
        raise ErroReconhecimentoSpeech("Nenhuma fala foi reconhecida no arquivo")
    if resultado.reason == speechsdk.ResultReason.Canceled:
        cancelamento = speechsdk.CancellationDetails.from_result(resultado)
        raise ErroReconhecimentoSpeech(
            f"Reconhecimento cancelado pelo Azure Speech: {cancelamento.reason}"
        )
    raise ErroReconhecimentoSpeech("O Azure Speech devolveu um resultado inesperado")


def _url_emissao(regiao: str) -> str:
    """Monta o endpoint de token pelo domínio configurado ou pela região."""
    endpoint = settings.speech_endpoint.strip().rstrip("/")
    if endpoint:
        return f"{endpoint}/sts/v1.0/issueToken"
    return f"https://{regiao}.api.cognitive.microsoft.com/sts/v1.0/issueToken"


async def emitir_token(*, cliente: httpx.AsyncClient | None = None) -> TokenVoz:
    """Solicita ao Azure Speech um token de curta duração.

    Chamado por api/routes/voz.py, que exige sessão válida: um endpoint
    aberto seria um proxy gratuito para o recurso de Speech do parceiro.
    """
    chave = settings.speech_key.strip()
    regiao = settings.speech_region.strip()
    idioma = settings.speech_idioma.strip() or "pt-BR"
    if not chave:
        raise ErroConfiguracaoSpeech("SPEECH_KEY não configurada")
    if not regiao:
        raise ErroConfiguracaoSpeech("SPEECH_REGION não configurada")
    proprio_cliente = cliente is None
    if proprio_cliente:
        cliente = httpx.AsyncClient(timeout=settings.speech_timeout_seconds)
    try:
        assert cliente is not None
        resposta = await cliente.post(
            _url_emissao(regiao),
            headers={"Ocp-Apim-Subscription-Key": chave, "Content-Length": "0"},
        )
    except httpx.HTTPError as erro:
        logger.warning("Emissão de token do Speech falhou: %s", type(erro).__name__)
        raise ErroTokenSpeech("Não foi possível acessar o Azure Speech") from None
    finally:
        if proprio_cliente and cliente is not None:
            await cliente.aclose()

    if resposta.status_code == 429:
        logger.warning("Emissão de token do Speech recusada: HTTP 429")
        raise ErroTokenSpeech(
            "Azure Speech respondeu HTTP 429: limite temporário atingido",
            cota_excedida=True,
        )
    if resposta.status_code >= 400:
        logger.warning("Emissão de token do Speech recusada: HTTP %s", resposta.status_code)
        raise ErroTokenSpeech(f"Azure Speech respondeu HTTP {resposta.status_code}")
    token = resposta.text.strip()
    if not token:
        raise ErroTokenSpeech("O Azure Speech devolveu um token vazio")
    return TokenVoz(token=token, regiao=regiao, idioma=idioma)


def main() -> None:
    """Executa o smoke test: ``python -m app.voz.speech audio.wav``."""
    parser = argparse.ArgumentParser(description="Valida o Azure Speech com um arquivo WAV")
    parser.add_argument("arquivo", type=Path, help="WAV curto com uma única fala")
    args = parser.parse_args()
    resultado = reconhecer_arquivo_wav(args.arquivo)
    print(resultado.texto)


if __name__ == "__main__":
    main()
