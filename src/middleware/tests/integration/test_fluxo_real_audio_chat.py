"""Smoke opt-in do texto e da voz contra PostgreSQL e Speech reais.

Usa somente a frase sintética "Conte uma piada", que termina em recusa
antes de qualquer executor externo. A fala é fornecida por REAL_AUDIO_PATH.
"""

import os
import wave
from pathlib import Path
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select

from app.api import deps
from app.api.routes import voz
from app.config import settings
from app.executor.base import RespostaExecutor
from app.main import app
from app.persistence.models import Canal
from app.persistence.repository import UsuarioRepository
from app.persistence.sessao import fabrica_de_sessoes
from app.persistence.tabelas import (
    ConversaTabela,
    InteracaoTabela,
    TranscricaoAudioTabela,
    UsuarioTabela,
)
from app.schemas.usuario import Perfil, UsuarioAutenticado
from app.servicos import processamento_audio
from app.servicos.audio_service import AudioService
from app.voz.midia import MidiaAudio

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_REAL_AUDIO_PROCESSOR") != "1",
    reason="Defina RUN_REAL_AUDIO_PROCESSOR=1 para usar PostgreSQL e Azure Speech reais.",
)


async def test_texto_e_voz_gravam_interacoes_com_processador_real(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    caminho_audio = Path(os.environ["REAL_AUDIO_PATH"])
    if not caminho_audio.is_file():
        pytest.fail(f"REAL_AUDIO_PATH não existe: {caminho_audio}")
    if not settings.speech_key:
        pytest.fail("SPEECH_KEY não está configurada para a execução real.")

    audio_bytes = caminho_audio.read_bytes()
    with wave.open(str(caminho_audio), "rb") as arquivo_wav:
        duracao = arquivo_wav.getnframes() / arquivo_wav.getframerate()

    usuario_id = f"teste-real-{uuid4().hex}"
    usuario = UsuarioAutenticado(
        id=usuario_id,
        nome="Teste sintético de integração",
        perfil=Perfil.MEMBRO_EQUIPE,
    )

    class ExecutorBloqueado:
        async def enviar(self, *args, **kwargs) -> RespostaExecutor:
            pytest.fail("Uma solicitação de fora de escopo não deve chamar executor externo.")

    async def preparar_usuario() -> None:
        async with fabrica_de_sessoes()() as sessao:
            await UsuarioRepository(sessao).garantir(
                usuario_id=usuario.id,
                nome=usuario.nome,
                perfil=usuario.perfil.value,
                email=None,
            )
            await sessao.commit()

    async def limpar_dados() -> None:
        async with fabrica_de_sessoes()() as sessao:
            await sessao.execute(
                delete(TranscricaoAudioTabela).where(
                    TranscricaoAudioTabela.usuario_id == usuario_id
                )
            )
            await sessao.execute(
                delete(InteracaoTabela).where(InteracaoTabela.usuario_id == usuario_id)
            )
            await sessao.execute(
                delete(ConversaTabela).where(ConversaTabela.usuario_id == usuario_id)
            )
            await sessao.execute(delete(UsuarioTabela).where(UsuarioTabela.id == usuario_id))
            await sessao.commit()

    monkeypatch.setattr(settings, "base_dir", tmp_path)
    monkeypatch.setattr(voz, "audio_service", AudioService())
    monkeypatch.setattr(
        voz,
        "inspecionar_audio",
        lambda _caminho: MidiaAudio(duracao_segundos=duracao),
    )
    overrides_anteriores = app.dependency_overrides.copy()
    app.dependency_overrides[deps.obter_usuario_atual] = lambda: usuario
    app.dependency_overrides[deps.obter_executor] = lambda: ExecutorBloqueado()
    monkeypatch.setattr(
        processamento_audio,
        "montar_executor",
        lambda *_args, **_kwargs: ExecutorBloqueado(),
    )

    async with app.router.lifespan_context(app):
        await preparar_usuario()
        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://middleware.test",
            ) as cliente:
                texto = await cliente.post("/chat", json={"mensagem": "Conte uma piada"})
                assert texto.status_code == 200, texto.text
                assert texto.json()["desfecho"] == "recusada_fora_escopo"
                assert texto.json()["resposta"]

                upload = await cliente.post(
                    "/voz/audios",
                    files={"audio": ("fala-sintetica.wav", audio_bytes, "audio/wav")},
                    data={"idioma": "pt-BR"},
                )
                assert upload.status_code == 202, upload.text
                transcricao = await cliente.get(upload.json()["consultar_em"])
                assert transcricao.status_code == 200, transcricao.text
                assert transcricao.json()["estado"] == "concluida"
                assert "piada" in transcricao.json()["texto"].casefold()
                assert transcricao.json()["interacao_id"]
                assert transcricao.json()["conversa_id"]

            async with fabrica_de_sessoes()() as sessao:
                linhas = await sessao.execute(
                    select(InteracaoTabela)
                    .where(InteracaoTabela.usuario_id == usuario_id)
                    .order_by(InteracaoTabela.criada_em)
                )
                interacoes = [linha.to_dominio() for linha in linhas.scalars()]

            assert len(interacoes) == 2
            assert interacoes[0].canal is Canal.CHAT
            assert interacoes[0].desfecho.value == "recusada_fora_escopo"
            assert interacoes[1].canal is Canal.VOZ
            assert interacoes[1].desfecho.value == "recusada_fora_escopo"
            assert interacoes[1].id == transcricao.json()["interacao_id"]
        finally:
            app.dependency_overrides.clear()
            app.dependency_overrides.update(overrides_anteriores)
            await limpar_dados()
