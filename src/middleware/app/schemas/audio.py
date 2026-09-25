"""Contratos da API de recebimento de áudios.

Conforme especificado na seção 5.7.3 do projeto.md, a API de voz aceita
submissões assíncronas de áudio para transcrição via Azure AI Speech.
Este módulo define os schemas de resposta para os endpoints de submissão
e consulta de transcrição.
"""

from typing import Any

from pydantic import BaseModel, Field


class ErroAudioResponse(BaseModel):
    """Envelope estavel dos erros publicos do canal de voz."""

    codigo: str
    mensagem: str
    detalhe: dict[str, Any] | None = None


class AudioUploadResponse(BaseModel):
    """Resposta à submissão de áudio para transcrição.

    Devolvida ao cliente quando o áudio é aceito e enfileirado para
    processamento. O estado é sempre "recebido" nesta resposta.
    """

    id_audio: str = Field(
        description="Identificador único da submissão, usado na consulta"
    )
    estado: str = Field(
        default="recebido",
        description="Estado da submissão. Sempre 'recebido' nesta resposta"
    )
    duracao_segundos: float = Field(
        description="Duração do áudio em segundos, apurada na validação"
    )
    consultar_em: str = Field(
        description="Caminho da consulta de transcrição"
    )
    expira_em: str = Field(
        description="Momento ISO 8601 em que o resultado deixa de estar disponível"
    )


class TranscricaoResponse(BaseModel):
    """Resposta à consulta de transcrição de áudio.

    O estado varia conforme o progresso: recebido, transcrevendo,
    concluida ou falhou. Campos específicos dependem do estado.
    """

    id_audio: str = Field(
        description="Identificador da submissão"
    )
    estado: str = Field(
        description="Estado da submissão: recebido, transcrevendo, concluida ou falhou"
    )
    texto: str | None = Field(
        default=None,
        description="Transcrição produzida (presente apenas no estado 'concluida')"
    )
    idioma: str | None = Field(
        default=None,
        description="Código BCP 47 do idioma detectado (presente apenas no estado 'concluida')"
    )
    confianca: float | None = Field(
        default=None,
        description="Grau de confiança do serviço de fala, entre 0 e 1 (presente apenas no estado 'concluida')"
    )
    duracao_segundos: float | None = Field(
        default=None,
        description="Duração do áudio em segundos (presente nos estados 'concluida' e 'falhou')"
    )
    latencia_ms: int | None = Field(
        default=None,
        description="Tempo entre aceitação e conclusão em milissegundos (presente apenas no estado 'concluida')"
    )
    mensagem_erro: str | None = Field(
        default=None,
        description="Orientação ao usuário quando a transcrição falha (presente apenas no estado 'falhou')"
    )
    conversa_id: str | None = Field(
        default=None,
        description="Conversa criada ou continuada pelo texto transcrito",
    )
    interacao_id: str | None = Field(
        default=None,
        description="Registro persistido pelo pipeline para esta fala",
    )
