"""Dubles pequenos para testar o contrato HTTP de audio sem PostgreSQL."""

from app.persistence.models import EstadoTranscricao
from app.voz.transcricao import ErroTranscricao


class BancoFalso:
    async def commit(self) -> None:
        pass


class RepositorioAudioMemoria:
    def __init__(self) -> None:
        self.audios = {}

    async def criar(self, audio) -> None:
        self.audios[audio.id] = audio

    async def obter(self, audio_id, usuario_id):
        audio = self.audios.get(audio_id)
        return audio if audio is not None and audio.usuario_id == usuario_id else None

    async def atualizar(self, audio_id, *, estado, **campos) -> None:
        audio = self.audios[audio_id]
        audio.estado = estado
        for nome, valor in campos.items():
            if valor is not None and hasattr(audio, nome):
                setattr(audio, nome, valor)


class ProcessadorAudioFalso:
    def __init__(self, repositorio, transcrever) -> None:
        self.repositorio = repositorio
        self.transcrever = transcrever

    async def processar(self, audio_id, caminho, idioma, usuario, conversa_id) -> None:
        await self.repositorio.atualizar(
            audio_id,
            estado=EstadoTranscricao.TRANSCREVENDO,
        )
        try:
            resultado = await self.transcrever(caminho, idioma=idioma)
        except ErroTranscricao as erro:
            await self.repositorio.atualizar(
                audio_id,
                estado=EstadoTranscricao.FALHOU,
                mensagem_erro=erro.mensagem,
            )
        else:
            await self.repositorio.atualizar(
                audio_id,
                estado=EstadoTranscricao.CONCLUIDA,
                texto=resultado.texto,
                idioma=resultado.idioma,
                confianca=resultado.confianca,
                duracao_segundos=resultado.duracao_segundos,
                latencia_ms=resultado.latencia_ms,
                conversa_id=conversa_id,
            )
        finally:
            caminho.unlink(missing_ok=True)
