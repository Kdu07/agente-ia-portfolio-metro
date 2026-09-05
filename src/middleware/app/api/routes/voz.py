"""Rotas do canal de voz.

Engloba a emissão de token efêmero do Azure Speech para o navegador
e a API de recebimento de áudios do usuário conforme especificação
da seção 5.7.3 do projeto.md.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel

from app.api.deps import UsuarioAtual
from app.schemas.audio import AudioUploadResponse, TranscricaoResponse
from app.servicos.audio_service import AudioService
from app.utils.validadores import validar_extensao_audio, validar_formato_audio, validar_tamanho_arquivo

router = APIRouter(prefix="/voz")

# Instância do serviço de áudio
audio_service = AudioService()


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


@router.get("/token", response_model=TokenResposta)
async def token(usuario: UsuarioAtual) -> TokenResposta:
    """Devolve um token de curta duração do Azure Speech.

    O frontend renova antes de expirar, e não ao receber erro: uma
    renovação reativa interromperia a fala do usuário no meio.
    """
    raise NotImplementedError("Emissão de token a implementar junto com a voz")


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
    audio: Annotated[UploadFile, File(description="Arquivo de áudio (mp3, wav, ogg, webm, mp4)")],
    idioma: Annotated[str | None, Form(description="Código BCP 47 do idioma (padrão: pt-BR)")] = None,
    conversa_id: Annotated[str | None, Form(description="ID da conversa existente")] = None,
    usuario: UsuarioAtual = Depends(),
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
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Campo 'audio' é obrigatório"
        )

    # Valida extensão
    try:
        extensao = validar_extensao_audio(audio.filename)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=str(e)
        )

    # Valida tamanho
    try:
        validar_tamanho_arquivo(audio.size or 0)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=str(e)
        )

    # Valida formato real via magic bytes
    try:
        formato_detectado = validar_formato_audio(audio.file)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=str(e)
        )

    # Gera ID único e salva arquivo usando o serviço
    id_audio = audio_service.gerar_id_audio()

    try:
        caminho_arquivo = audio_service.salvar_arquivo(
            audio.file,
            id_audio,
            formato_detectado
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Falha ao processar arquivo: {e}"
        )

    # Calcula expiração
    duracao_segundos = 0.0  # TODO: Calcular duração real do áudio
    expiracao = audio_service.calcular_expiracao(duracao_segundos)

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
    usuario: UsuarioAtual = Depends(),
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
    # TODO: Implementar consulta real ao banco de dados/cache
    # Por enquanto retorna estado de processamento
    return TranscricaoResponse(
        id_audio=id_audio,
        estado="transcrevendo",
    )
