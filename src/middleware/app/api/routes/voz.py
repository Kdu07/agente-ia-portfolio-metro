"""Rotas do canal de voz.

Engloba a emissão de token efêmero do Azure Speech para o navegador
e a API de recebimento de áudios do usuário conforme especificação
da seção 5.7.3 do projeto.md.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from pydantic import BaseModel

from app.api.deps import UsuarioAtual
from app.schemas.audio import AudioUploadResponse, TranscricaoResponse
from app.utils.validadores import validar_extensao_audio, validar_formato_audio, validar_tamanho_arquivo

router = APIRouter(prefix="/voz")


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


@router.post("/audios", status_code=status.HTTP_202_ACCEPTED, response_model=AudioUploadResponse)
async def upload_audio(
    audio: Annotated[UploadFile, File(description="Arquivo de áudio (mp3, wav, ogg, webm, mp4)")],
    idioma: Annotated[str | None, Form(description="Código BCP 47 do idioma (padrão: pt-BR)")] = None,
    conversa_id: Annotated[str | None, Form(description="ID da conversa existente")] = None,
    usuario: UsuarioAtual = Depends(),
) -> AudioUploadResponse:
    """Submete um áudio para transcrição via Azure AI Speech.

    Valida formato, tamanho e duração antes de processar. A submissão
    é assíncrona: retorna 202 com ID para consulta posterior.

    Conforme especificação seção 5.7.3 do projeto.md.
    """
    # TODO: Implementar lógica completa de upload e processamento
    # Este é um esboço que valida e retorna estrutura básica

    # Valida extensão
    if audio.filename:
        validar_extensao_audio(audio.filename)

    # Valida tamanho
    validar_tamanho_arquivo(audio.size or 0)

    # Valida formato real via magic bytes
    formato_detectado = validar_formato_audio(audio.file)

    # TODO: Gerar ID único, salvar arquivo/processar, enfileirar transcrição
    # Por enquanto retorna estrutura esqueletica
    from uuid import uuid4

    id_audio = str(uuid4())

    return AudioUploadResponse(
        id_audio=id_audio,
        estado="recebido",
        duracao_segundos=0.0,  # TODO: Calcular duração real
        consultar_em=f"/voz/audios/{id_audio}/transcricao",
        expira_em="2026-09-03T18:00:00Z",  # TODO: Calcular expiração real
    )
