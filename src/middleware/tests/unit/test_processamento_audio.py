"""Costura real do processador de audio entre STT, pipeline e banco."""

from contextlib import asynccontextmanager
from typing import ClassVar

import pytest

from app.persistence.models import Canal, EstadoTranscricao
from app.schemas.chat import ChatResponse
from app.schemas.usuario import Perfil, UsuarioAutenticado
from app.servicos import processamento_audio as modulo
from app.voz.transcricao import ResultadoTranscricao


class SessaoFalsa:
    async def commit(self) -> None:
        pass

    async def rollback(self) -> None:
        pass


class AudiosFalso:
    atualizacoes: ClassVar[list] = []

    def __init__(self, _sessao) -> None:
        pass

    async def atualizar(self, audio_id, *, estado, **campos) -> None:
        self.atualizacoes.append((audio_id, estado, campos))


@pytest.mark.asyncio
async def test_processador_liga_transcricao_ao_pipeline_e_interacao(monkeypatch, tmp_path) -> None:
    AudiosFalso.atualizacoes = []
    arquivo = tmp_path / "fala.wav"
    arquivo.write_bytes(b"audio")
    usuario = UsuarioAutenticado(
        id="u-voz",
        nome="Pessoa",
        perfil=Perfil.LIDER_PROJETO,
    )
    chamadas = []

    @asynccontextmanager
    async def contexto():
        yield SessaoFalsa()

    async def transcrever(_caminho, *, idioma):
        return ResultadoTranscricao(
            texto="Qual o status do projeto?",
            idioma=idioma or "pt-BR",
            confianca=0.93,
            duracao_segundos=2.0,
            latencia_ms=120,
        )

    class OrquestradorFalso:
        def __init__(self, **_kwargs) -> None:
            pass

        async def processar(self, pedido, usuario_recebido, *, canal):
            chamadas.append((pedido, usuario_recebido, canal))
            return ChatResponse(
                resposta="Projeto em andamento",
                conversa_id="conversa-1",
                intencao_id="consultar_status_projeto",
                desfecho="encaminhada",
                interacao_id="interacao-1",
            )

    monkeypatch.setattr(modulo, "fabrica_de_sessoes", lambda: lambda: contexto())
    monkeypatch.setattr(modulo, "AudioRepository", AudiosFalso)
    monkeypatch.setattr(modulo, "InteracaoRepository", lambda _sessao: object())
    monkeypatch.setattr(modulo, "ConversaRepository", lambda _sessao: object())
    monkeypatch.setattr(modulo, "montar_executor", lambda *_args: object())
    monkeypatch.setattr(modulo, "Orquestrador", OrquestradorFalso)
    monkeypatch.setattr(modulo, "transcrever_arquivo", transcrever)

    await modulo.ProcessadorAudio().processar(
        "audio-1",
        arquivo,
        "pt-BR",
        usuario,
        None,
    )

    assert chamadas[0][0].mensagem == "Qual o status do projeto?"
    assert chamadas[0][0].canal is Canal.VOZ
    assert chamadas[0][2] is Canal.VOZ
    assert AudiosFalso.atualizacoes[0][1] is EstadoTranscricao.TRANSCREVENDO
    conclusao = AudiosFalso.atualizacoes[-1]
    assert conclusao[1] is EstadoTranscricao.CONCLUIDA
    assert conclusao[2]["interacao_id"] == "interacao-1"
    assert conclusao[2]["conversa_id"] == "conversa-1"
    assert not arquivo.exists()
