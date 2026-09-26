"""Processamento assincrono que liga STT, NLP e persistencia."""

import logging
from pathlib import Path

from app.executor.fabrica import montar_executor
from app.persistence.models import Canal, EstadoTranscricao
from app.persistence.repository import (
    AudioRepository,
    ConversaRepository,
    InteracaoRepository,
)
from app.persistence.sessao import fabrica_de_sessoes
from app.pipeline.orquestrador import Orquestrador
from app.schemas.chat import ChatRequest
from app.schemas.usuario import UsuarioAutenticado
from app.servicos.audio_service import AudioService
from app.voz.transcricao import ErroTranscricao, transcrever_arquivo

logger = logging.getLogger(__name__)


class ProcessadorAudio:
    """Executa uma submissao aceita fora do ciclo da requisicao HTTP."""

    async def processar(
        self,
        audio_id: str,
        caminho: Path,
        idioma: str | None,
        usuario: UsuarioAutenticado,
        conversa_id: str | None,
    ) -> None:
        await self._marcar_transcrevendo(audio_id)
        try:
            resultado = await transcrever_arquivo(caminho, idioma=idioma)
            await self._processar_texto(audio_id, resultado, usuario, conversa_id)
        except ErroTranscricao as erro:
            await self._marcar_falha(audio_id, erro.mensagem)
        except Exception:
            logger.exception("Falha inesperada ao processar audio %s", audio_id)
            await self._marcar_falha(
                audio_id,
                "Nao foi possivel concluir a transcricao e o processamento",
            )
        finally:
            AudioService().limpar_arquivo(caminho)

    async def _marcar_transcrevendo(self, audio_id: str) -> None:
        async with fabrica_de_sessoes()() as sessao:
            await AudioRepository(sessao).atualizar(
                audio_id,
                estado=EstadoTranscricao.TRANSCREVENDO,
            )
            await sessao.commit()

    async def _processar_texto(self, audio_id, resultado, usuario, conversa_id) -> None:
        """Grava interacao e conclusao do audio na mesma transacao."""
        async with fabrica_de_sessoes()() as sessao:
            try:
                orquestrador = Orquestrador(
                    executor=montar_executor(sessao, usuario),
                    interacoes=InteracaoRepository(sessao),
                    conversas=ConversaRepository(sessao),
                )
                resposta = await orquestrador.processar(
                    ChatRequest(
                        mensagem=resultado.texto,
                        conversa_id=conversa_id,
                        canal=Canal.VOZ,
                    ),
                    usuario,
                    canal=Canal.VOZ,
                )
                await AudioRepository(sessao).atualizar(
                    audio_id,
                    estado=EstadoTranscricao.CONCLUIDA,
                    conversa_id=resposta.conversa_id,
                    interacao_id=resposta.interacao_id,
                    texto=resultado.texto,
                    idioma=resultado.idioma,
                    confianca=resultado.confianca,
                    duracao_segundos=resultado.duracao_segundos,
                    latencia_ms=resultado.latencia_ms,
                )
                await sessao.commit()
            except Exception:
                await sessao.rollback()
                raise

    async def _marcar_falha(self, audio_id: str, mensagem: str) -> None:
        async with fabrica_de_sessoes()() as sessao:
            await AudioRepository(sessao).atualizar(
                audio_id,
                estado=EstadoTranscricao.FALHOU,
                mensagem_erro=mensagem,
            )
            await sessao.commit()
