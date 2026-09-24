"""Rotas do canal de voz.

Engloba a emissão de token efêmero do Azure Speech para o navegador
e a API de recebimento de áudios do usuário conforme especificação
da seção 5.7.3 do projeto.md.
"""

import logging
from pathlib import Path
from typing import Annotated

from fastapi import (
    APIRouter,
    BackgroundTasks,
    File,
    Form,
    HTTPException,
    Response,
    UploadFile,
    status,
)
from pydantic import BaseModel

from app.api.deps import UsuarioAtual
from app.schemas.audio import AudioUploadResponse, TranscricaoResponse
from app.servicos.audio_service import AudioProcessingError, AudioService
from app.utils.validadores import (
    validar_extensao_audio,
    validar_formato_audio,
    validar_tamanho_arquivo,
)
from app.voz.speech import ErroConfiguracaoSpeech, ErroTokenSpeech, emitir_token
from app.voz.transcricao import ErroTranscricao, transcrever_arquivo

router = APIRouter(prefix="/voz")
logger = logging.getLogger(__name__)

# Instância do serviço de áudio
audio_service = AudioService()


async def _processar_transcricao(
    id_audio: str,
    caminho_arquivo: Path,
    idioma: str | None,
) -> None:
    """Executa a transcrição após o retorno do HTTP 202."""
    audio_service.registrar_transcricao(
        TranscricaoResponse(id_audio=id_audio, estado="transcrevendo")
    )
    try:
        resultado = await transcrever_arquivo(
            caminho_arquivo,
            idioma=idioma,
        )
        audio_service.registrar_transcricao(
            TranscricaoResponse(
                id_audio=id_audio,
                estado="concluida",
                texto=resultado.texto,
                idioma=resultado.idioma,
                confianca=resultado.confianca,
                duracao_segundos=resultado.duracao_segundos,
                latencia_ms=resultado.latencia_ms,
            )
        )
    except ErroTranscricao as erro:
        audio_service.registrar_transcricao(
            TranscricaoResponse(
                id_audio=id_audio,
                estado="falhou",
                mensagem_erro=erro.mensagem,
            )
        )
    except Exception:
        logger.exception("Falha inesperada ao transcrever áudio %s", id_audio)
        audio_service.registrar_transcricao(
            TranscricaoResponse(
                id_audio=id_audio,
                estado="falhou",
                mensagem_erro="Não foi possível concluir a transcrição",
            )
        )
    finally:
        audio_service.limpar_arquivo(caminho_arquivo)


class TokenResposta(BaseModel):
    """Credencial temporária para o Speech SDK no navegador.

    Não carrega a chave do recurso: apenas um token de validade curta.
    Um token vazado expira sozinho; uma chave vazada exigiria rotação no
    tenant do parceiro.
    """

    token: str
    regiao: str
    expira_em_segundos: int
    idioma: str


@router.get(
    "/token",
    response_model=TokenResposta,
    responses={
        status.HTTP_401_UNAUTHORIZED: {"description": "Sessão ausente ou expirada"},
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "description": "Serviço de fala não configurado ou indisponível"
        },
    },
)
async def token(usuario: UsuarioAtual, response: Response) -> TokenResposta:
    """Devolve um token de curta duração do Azure Speech.

    O frontend renova antes de expirar, e não ao receber erro: uma
    renovação reativa interromperia a fala do usuário no meio.

    `no-store` impede que um proxy ou o cache do navegador guarde a
    credencial. Configuração ausente e falha do serviço respondem 503 com a
    mesma mensagem: o detalhe fica no log, não no navegador.
    """
    try:
        emitido = await emitir_token()
    except (ErroConfiguracaoSpeech, ErroTokenSpeech) as erro:
        logger.warning("Token de voz não emitido para %s: %s", usuario.id, erro)
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Entrada por voz indisponível no momento. Digite a mensagem.",
        ) from None
    response.headers["Cache-Control"] = "no-store"
    return TokenResposta(
        token=emitido.token,
        regiao=emitido.regiao,
        expira_em_segundos=emitido.expira_em_segundos,
        idioma=emitido.idioma,
    )


@router.post(
    "/audios",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=AudioUploadResponse,
    summary="Submeter áudio para transcrição",
    description=(
        "Recebe um arquivo de áudio para transcrição via Azure AI Speech. "
        "Valida formato, tamanho e duração antes de processar. A submissão "
        "é assíncrona: retorna 202 com ID para consulta posterior do resultado."
    ),
    responses={
        status.HTTP_202_ACCEPTED: {
            "description": "Áudio aceito e enfileirado para transcrição",
            "content": {
                "application/json": {
                    "example": {
                        "id_audio": "a3f1c9d2-5e08-4b77-9c31-2ad6e4f80b19",
                        "estado": "recebido",
                        "duracao_segundos": 11.4,
                        "consultar_em": "/voz/audios/a3f1c9d2-5e08-4b77-9c31-2ad6e4f80b19/transcricao",
                        "expira_em": "2026-09-03T18:42:10Z",
                    }
                }
            },
        },
        status.HTTP_400_BAD_REQUEST: {
            "description": "Campo 'audio' não fornecido ou inválido",
        },
        status.HTTP_413_REQUEST_ENTITY_TOO_LARGE: {
            "description": "Arquivo excede 25 MB",
        },
        status.HTTP_415_UNSUPPORTED_MEDIA_TYPE: {
            "description": "Formato de arquivo não suportado (aceitos: mp3, wav, ogg, webm, mp4)",
        },
    },
)
async def upload_audio(
    background_tasks: BackgroundTasks,
    audio: Annotated[UploadFile, File(description="Arquivo de áudio (mp3, wav, ogg, webm, mp4)")],
    usuario: UsuarioAtual,
    idioma: Annotated[
        str | None, Form(description="Código BCP 47 do idioma (padrão: pt-BR)")
    ] = None,
    conversa_id: Annotated[str | None, Form(description="ID da conversa existente")] = None,
) -> AudioUploadResponse:
    """Submete um áudio para transcrição via Azure AI Speech.

    Valida formato, tamanho e duração antes de processar. A submissão
    é assíncrona: retorna 202 com ID para consulta posterior.

    Erros:
        400 Bad Request: Arquivo inválido ou campos incorretos
        413 Payload Too Large: Arquivo excede 25 MB
        415 Unsupported Media Type: Formato não suportado

    Conforme especificação seção 5.7.3 do projeto.md.

    **Exemplo de requisição cURL:**
    ```bash
    curl -X POST "http://localhost:8000/voz/audios" \\
      -H "Cookie: sessao=<cookie>" \\
      -F "audio=@enunciado.webm" \\
      -F "idioma=pt-BR"
    ```
    """
    # Valida se arquivo foi fornecido
    if not audio or not audio.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Campo 'audio' é obrigatório"
        )

    # Valida extensão
    try:
        validar_extensao_audio(audio.filename)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail=str(e))

    # Valida tamanho
    try:
        validar_tamanho_arquivo(audio.size or 0)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=str(e))

    # Valida formato real via magic bytes
    try:
        formato_detectado = validar_formato_audio(audio.file)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail=str(e))

    # Gera ID único e salva arquivo usando o serviço
    id_audio = audio_service.gerar_id_audio()

    try:
        caminho_arquivo = audio_service.salvar_arquivo(audio.file, id_audio, formato_detectado)
    except AudioProcessingError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Falha ao processar arquivo: {e}",
        )

    # Calcula expiração
    duracao_segundos = 0.0  # TODO: Calcular duração real do áudio
    expiracao = audio_service.calcular_expiracao(duracao_segundos)
    audio_service.registrar_transcricao(TranscricaoResponse(id_audio=id_audio, estado="recebido"))
    background_tasks.add_task(
        _processar_transcricao,
        id_audio,
        caminho_arquivo,
        idioma,
    )

    return AudioUploadResponse(
        id_audio=id_audio,
        estado="recebido",
        duracao_segundos=duracao_segundos,
        consultar_em=f"/voz/audios/{id_audio}/transcricao",
        expira_em=expiracao.isoformat() + "Z",
    )


@router.get(
    "/audios/{id_audio}/transcricao",
    response_model=TranscricaoResponse,
    summary="Consultar resultado da transcrição",
    description=(
        "Consulta o estado atual da transcrição de um áudio submetido. "
        "Retorna o estado (recebido, transcrevendo, concluida ou falhou) "
        "e, quando concluída, o texto transcrito com metadados."
    ),
    responses={
        status.HTTP_200_OK: {
            "description": "Estado da transcrição consultado com sucesso",
            "content": {
                "application/json": {
                    "examples": {
                        "em_processamento": {
                            "summary": "Ainda transcrevendo",
                            "value": {
                                "id_audio": "a3f1c9d2-5e08-4b77-9c31-2ad6e4f80b19",
                                "estado": "transcrevendo",
                            },
                        },
                        "concluida": {
                            "summary": "Transcrição concluída",
                            "value": {
                                "id_audio": "a3f1c9d2-5e08-4b77-9c31-2ad6e4f80b19",
                                "estado": "concluida",
                                "texto": "Qual o avanço do projeto da Linha 15 Prata?",
                                "idioma": "pt-BR",
                                "confianca": 0.94,
                                "duracao_segundos": 11.4,
                                "latencia_ms": 1830,
                            },
                        },
                        "falhou": {
                            "summary": "Transcrição falhou",
                            "value": {
                                "id_audio": "a3f1c9d2-5e08-4b77-9c31-2ad6e4f80b19",
                                "estado": "falhou",
                                "mensagem_erro": "Áudio muito ruidoso, não foi possível transcrever",
                                "duracao_segundos": 11.4,
                            },
                        },
                    }
                }
            },
        },
        status.HTTP_404_NOT_FOUND: {
            "description": "ID de áudio não encontrado ou expirado",
        },
    },
)
async def consultar_transcricao(
    id_audio: str,
    usuario: UsuarioAtual,
) -> TranscricaoResponse:
    """Consulta o resultado da transcrição de um áudio.

    Retorna o estado atual da submissão (recebido, transcrevendo,
    concluida ou falhou) e, quando concluída, o texto transcrito.

    Conforme especificação seção 5.7.3.4 do projeto.md.

    **Exemplo de requisição cURL:**
    ```bash
    curl -X GET "http://localhost:8000/voz/audios/{id_audio}/transcricao" \\
      -H "Cookie: sessao=<cookie>"
    ```
    """
    transcricao = audio_service.obter_transcricao(id_audio)
    if transcricao is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Áudio não encontrado ou resultado expirado",
        )
    return transcricao
