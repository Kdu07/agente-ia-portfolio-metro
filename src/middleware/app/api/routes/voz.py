"""Rotas do canal de voz.

Engloba a emissão de token efêmero do Azure Speech para o navegador
e a API de recebimento de áudios do usuário conforme especificação
da seção 5.7.3 do projeto.md.
"""

import logging
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    Request,
    Response,
    UploadFile,
    status,
)
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.api.deps import (
    SessaoBanco,
    UsuarioAtual,
    obter_audios,
    obter_processador_audio,
)
from app.persistence.models import EstadoTranscricao, TranscricaoAudio
from app.persistence.repository import AudioRepository
from app.schemas.audio import AudioUploadResponse, ErroAudioResponse, TranscricaoResponse
from app.servicos.audio_service import AudioProcessingError, AudioService
from app.servicos.processamento_audio import ProcessadorAudio
from app.utils.validadores import (
    validar_extensao_audio,
    validar_formato_audio,
    validar_tamanho_arquivo,
)
from app.voz.midia import (
    LIMITE_DURACAO_SEGUNDOS,
    AudioMuitoLongo,
    ErroMidia,
    InspecaoMidiaIndisponivel,
    inspecionar_audio,
    validar_duracao,
)
from app.voz.speech import (
    ErroConfiguracaoSpeech,
    ErroTokenSpeech,
    emitir_token,
)

router = APIRouter(prefix="/voz")
logger = logging.getLogger(__name__)

# Instância do serviço de áudio
audio_service = AudioService()


class ErroAudioApi(Exception):
    """Erro publico com corpo estavel conforme o contrato do canal de voz."""

    def __init__(
        self,
        status_code: int,
        codigo: str,
        mensagem: str,
        detalhe: dict[str, Any] | None = None,
    ) -> None:
        self.status_code = status_code
        self.resposta = ErroAudioResponse(
            codigo=codigo,
            mensagem=mensagem,
            detalhe=detalhe,
        )


async def tratar_erro_audio(_request: Request, erro: ErroAudioApi) -> JSONResponse:
    """Serializa o erro sem o envelope ``detail`` do HTTPException."""
    return JSONResponse(
        status_code=erro.status_code,
        content=erro.resposta.model_dump(exclude_none=True),
    )


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
        status.HTTP_429_TOO_MANY_REQUESTS: {"description": "Cota temporária excedida"},
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "description": "Serviço de fala não configurado ou indisponível"
        },
    },
)
async def token(usuario: UsuarioAtual, response: Response) -> TokenResposta:
    """Devolve um token de curta duração do Azure Speech.

    O frontend renova antes de expirar, e não ao receber erro: uma
    renovação reativa interromperia a fala do usuário no meio.
    """
    response.headers["Cache-Control"] = "no-store"
    try:
        credencial = await emitir_token()
    except ErroConfiguracaoSpeech as erro:
        logger.error("Configuração do Azure Speech inválida: %s", erro)
        raise ErroAudioApi(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "SERVICO_INDISPONIVEL",
            "O canal de voz está temporariamente indisponível.",
        ) from erro
    except ErroTokenSpeech as erro:
        logger.warning("Falha ao emitir token do Azure Speech: %s", erro)
        codigo = "COTA_EXCEDIDA" if erro.cota_excedida else "SERVICO_INDISPONIVEL"
        http_status = (
            status.HTTP_429_TOO_MANY_REQUESTS
            if codigo == "COTA_EXCEDIDA"
            else status.HTTP_503_SERVICE_UNAVAILABLE
        )
        raise ErroAudioApi(
            http_status,
            codigo,
            "O canal de voz está temporariamente indisponível.",
        ) from erro
    return TokenResposta(
        token=credencial.token,
        regiao=credencial.regiao,
        expira_em_segundos=credencial.expira_em_segundos,
        idioma=credencial.idioma,
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
    usuario: UsuarioAtual,
    banco: SessaoBanco,
    audios: Annotated[AudioRepository, Depends(obter_audios)],
    processador: Annotated[ProcessadorAudio, Depends(obter_processador_audio)],
    audio: Annotated[
        UploadFile | None,
        File(description="Arquivo de áudio (mp3, wav, ogg, webm, mp4)"),
    ] = None,
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
        raise ErroAudioApi(
            status.HTTP_400_BAD_REQUEST,
            "AUDIO_AUSENTE",
            "Não recebi nenhum áudio. Tente gravar de novo.",
        )

    # Valida extensão
    try:
        extensao = validar_extensao_audio(audio.filename)
    except ValueError as erro:
        raise ErroAudioApi(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            "AUDIO_FORMATO_NAO_SUPORTADO",
            "Não consigo ler esse formato de áudio.",
        ) from erro

    # Valida tamanho
    try:
        if audio.size is not None:
            validar_tamanho_arquivo(audio.size)
    except ValueError as erro:
        raise ErroAudioApi(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            "AUDIO_MUITO_GRANDE",
            "O arquivo é grande demais.",
            {"bytes": audio.size, "limite_bytes": 25 * 1024 * 1024},
        ) from erro

    # Valida formato real via magic bytes
    try:
        formato_detectado = validar_formato_audio(audio.file)
    except ValueError as erro:
        raise ErroAudioApi(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            "AUDIO_FORMATO_NAO_SUPORTADO",
            "Não consigo ler esse formato de áudio.",
        ) from erro
    if formato_detectado != extensao:
        raise ErroAudioApi(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            "AUDIO_FORMATO_NAO_SUPORTADO",
            "A extensão do arquivo não corresponde ao conteúdo enviado.",
        )

    # Gera ID único e salva arquivo usando o serviço
    id_audio = audio_service.gerar_id_audio()

    try:
        caminho_arquivo = audio_service.salvar_arquivo(audio.file, id_audio, formato_detectado)
    except AudioProcessingError as erro:
        raise ErroAudioApi(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "FALHA_INTERNA",
            "Não foi possível armazenar o áudio recebido.",
        ) from erro

    try:
        validar_tamanho_arquivo(caminho_arquivo.stat().st_size)
        midia = inspecionar_audio(caminho_arquivo)
        validar_duracao(midia.duracao_segundos)
    except AudioMuitoLongo as erro:
        audio_service.limpar_arquivo(caminho_arquivo)
        raise ErroAudioApi(
            status.HTTP_400_BAD_REQUEST,
            "AUDIO_MUITO_LONGO",
            "O áudio tem mais de 5 minutos. Grave um trecho mais curto ou digite a solicitação.",
            {
                "duracao_segundos": erro.duracao_segundos,
                "limite_segundos": LIMITE_DURACAO_SEGUNDOS,
            },
        ) from erro
    except ErroMidia as erro:
        audio_service.limpar_arquivo(caminho_arquivo)
        raise ErroAudioApi(
            status.HTTP_400_BAD_REQUEST,
            "AUDIO_ILEGIVEL",
            "Não consegui abrir esse áudio. Tente gravar de novo.",
        ) from erro
    except ValueError as erro:
        audio_service.limpar_arquivo(caminho_arquivo)
        raise ErroAudioApi(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            "AUDIO_MUITO_GRANDE",
            "O arquivo é grande demais.",
            {
                "bytes": caminho_arquivo.stat().st_size if caminho_arquivo.exists() else None,
                "limite_bytes": 25 * 1024 * 1024,
            },
        ) from erro
    except InspecaoMidiaIndisponivel as erro:
        audio_service.limpar_arquivo(caminho_arquivo)
        logger.exception("Validador de mídia indisponível")
        raise ErroAudioApi(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "SERVICO_INDISPONIVEL",
            "Não foi possível validar o áudio agora. Tente novamente.",
        ) from erro

    duracao_segundos = midia.duracao_segundos
    expiracao = audio_service.calcular_expiracao(duracao_segundos)
    await audios.criar(
        TranscricaoAudio(
            id=id_audio,
            usuario_id=usuario.id,
            estado=EstadoTranscricao.RECEBIDO,
            formato=formato_detectado,
            duracao_segundos=duracao_segundos,
            criada_em=datetime.now(UTC),
            expira_em=expiracao,
        )
    )
    # O processamento abre outra sessao e precisa enxergar a submissao.
    await banco.commit()
    background_tasks.add_task(
        processador.processar,
        id_audio,
        caminho_arquivo,
        idioma,
        usuario,
        conversa_id,
    )

    return AudioUploadResponse(
        id_audio=id_audio,
        estado="recebido",
        duracao_segundos=duracao_segundos,
        consultar_em=f"/voz/audios/{id_audio}/transcricao",
        expira_em=expiracao.isoformat().replace("+00:00", "Z"),
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
    audios: Annotated[AudioRepository, Depends(obter_audios)],
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
    transcricao = await audios.obter(id_audio, usuario.id)
    if transcricao is None:
        raise ErroAudioApi(
            status.HTTP_404_NOT_FOUND,
            "AUDIO_NAO_ENCONTRADO",
            "Esse áudio não está mais disponível.",
        )
    return TranscricaoResponse(
        id_audio=transcricao.id,
        estado=transcricao.estado.value,
        texto=transcricao.texto,
        idioma=transcricao.idioma,
        confianca=transcricao.confianca,
        duracao_segundos=transcricao.duracao_segundos,
        latencia_ms=transcricao.latencia_ms,
        mensagem_erro=transcricao.mensagem_erro,
        conversa_id=transcricao.conversa_id,
        interacao_id=transcricao.interacao_id,
    )
