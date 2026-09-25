"""Casos TF-RF02-01 a TF-RF02-07 — interação por texto e voz."""

import pytest
from fastapi.testclient import TestClient

from app.api import deps
from app.api.routes import voz
from app.config import settings
from app.main import app
from app.persistence.models import Canal, EstadoTranscricao
from app.pipeline.desfechos import Desfecho
from app.pipeline.orquestrador import Orquestrador
from app.schemas.chat import ChatRequest
from app.schemas.usuario import Perfil, UsuarioAutenticado
from app.servicos.audio_service import AudioService
from app.voz.midia import ErroMidia, MidiaAudio
from app.voz.transcricao import ErroTranscricao, ResultadoTranscricao
from tests.apoio_audio import BancoFalso, RepositorioAudioMemoria

USUARIO = UsuarioAutenticado("rf02", "Teste RF02", Perfil.LIDER_PROJETO)
WAV = b"RIFF" + b"\x00" * 100


@pytest.fixture
def ambiente(tmp_path, monkeypatch, pipeline_controlado, executor_espiao, repositorio_memoria):
    async def transcrever(caminho, *, idioma):
        return ResultadoTranscricao(
            texto="Qual o status do Projeto Verde?",
            idioma=idioma or "pt-BR",
            confianca=0.95,
            duracao_segundos=1.2,
            latencia_ms=10,
        )

    monkeypatch.setattr(settings, "base_dir", tmp_path)
    monkeypatch.setattr(voz, "audio_service", AudioService())
    monkeypatch.setattr(
        voz,
        "inspecionar_audio",
        lambda _caminho: MidiaAudio(duracao_segundos=1.2),
    )
    audios = RepositorioAudioMemoria()

    class Processador:
        def __init__(self) -> None:
            self.transcrever = transcrever

        async def processar(self, audio_id, caminho, idioma, usuario, conversa_id) -> None:
            try:
                resultado = await self.transcrever(caminho, idioma=idioma)
                resposta = await Orquestrador(
                    executor_espiao,
                    repositorio_memoria,
                    repositorio_memoria,
                ).processar(
                    ChatRequest(
                        mensagem=resultado.texto,
                        conversa_id=conversa_id,
                        canal=Canal.VOZ,
                    ),
                    usuario,
                    canal=Canal.VOZ,
                )
                await audios.atualizar(
                    audio_id,
                    estado=EstadoTranscricao.CONCLUIDA,
                    texto=resultado.texto,
                    idioma=resultado.idioma,
                    confianca=resultado.confianca,
                    duracao_segundos=resultado.duracao_segundos,
                    latencia_ms=resultado.latencia_ms,
                    conversa_id=resposta.conversa_id,
                    interacao_id=resposta.interacao_id,
                )
            except ErroTranscricao as erro:
                await audios.atualizar(
                    audio_id,
                    estado=EstadoTranscricao.FALHOU,
                    mensagem_erro=erro.mensagem,
                )
            finally:
                caminho.unlink(missing_ok=True)

    processador = Processador()
    app.dependency_overrides[deps.obter_usuario_atual] = lambda: USUARIO
    app.dependency_overrides[deps.obter_sessao] = lambda: BancoFalso()
    app.dependency_overrides[deps.obter_audios] = lambda: audios
    app.dependency_overrides[deps.obter_processador_audio] = lambda: processador
    app.dependency_overrides[deps.obter_orquestrador] = lambda: Orquestrador(
        executor_espiao, repositorio_memoria, repositorio_memoria
    )
    try:
        with TestClient(app) as cliente:
            yield cliente, executor_espiao, repositorio_memoria, processador
    finally:
        app.dependency_overrides.clear()


def test_tf_rf02_01_entrada_por_texto(ambiente) -> None:
    cliente, _, repositorio, _ = ambiente
    resposta = cliente.post("/chat", json={"mensagem": "Status do Projeto Verde"})
    assert resposta.status_code == 200
    assert resposta.json()["desfecho"] == Desfecho.ENCAMINHADA.value
    assert repositorio.interacoes[0].canal is Canal.CHAT


def test_tf_rf02_02_audio_percorre_upload_e_transcricao(ambiente) -> None:
    cliente, _, _, _ = ambiente
    upload = cliente.post(
        "/voz/audios", files={"audio": ("pergunta.wav", WAV, "audio/wav")}
    )
    consulta = cliente.get(upload.json()["consultar_em"])
    assert upload.status_code == 202
    assert consulta.status_code == 200
    assert consulta.json()["estado"] == "concluida"
    assert consulta.json()["texto"] == "Qual o status do Projeto Verde?"


def test_tf_rf02_03_formato_fora_dos_aceitos(ambiente) -> None:
    cliente, _, _, _ = ambiente
    resposta = cliente.post(
        "/voz/audios", files={"audio": ("arquivo.exe", b"MZpayload", "application/octet-stream")}
    )
    assert resposta.status_code == 415


def test_tf_rf02_04_audio_acima_de_cinco_minutos_e_recusado(ambiente, monkeypatch) -> None:
    cliente, _, _, _ = ambiente
    monkeypatch.setattr(
        voz,
        "inspecionar_audio",
        lambda _caminho: MidiaAudio(duracao_segundos=301.0),
    )
    resposta = cliente.post(
        "/voz/audios", files={"audio": ("longo.wav", WAV, "audio/wav")}
    )
    assert resposta.status_code == 400
    assert resposta.json()["codigo"] == "AUDIO_MUITO_LONGO"


def test_tf_rf02_05_arquivo_ilegivel_e_recusado_antes_do_stt(ambiente, monkeypatch) -> None:
    cliente, _, _, _ = ambiente

    def ilegivel(_caminho):
        raise ErroMidia("arquivo corrompido")

    monkeypatch.setattr(voz, "inspecionar_audio", ilegivel)
    resposta = cliente.post(
        "/voz/audios", files={"audio": ("corrompido.wav", b"RIFF", "audio/wav")}
    )
    assert resposta.status_code == 400
    assert resposta.json()["codigo"] == "AUDIO_ILEGIVEL"


def test_tf_rf02_06_audio_sem_fala_termina_no_estado_falhou(
    ambiente, monkeypatch
) -> None:
    cliente, _, _, processador = ambiente

    async def sem_fala(caminho, *, idioma):
        raise ErroTranscricao("FALA_NAO_RECONHECIDA", "Nenhuma fala reconhecida")

    processador.transcrever = sem_fala
    upload = cliente.post(
        "/voz/audios", files={"audio": ("silencio.wav", WAV, "audio/wav")}
    )
    consulta = cliente.get(upload.json()["consultar_em"])
    assert consulta.status_code == 200
    assert consulta.json()["estado"] == "falhou"
    assert consulta.json()["mensagem_erro"] == "Nenhuma fala reconhecida"


def test_tf_rf02_07_texto_transcrito_reentra_no_pipeline_como_voz(ambiente) -> None:
    cliente, executor, repositorio, _ = ambiente
    upload = cliente.post(
        "/voz/audios", files={"audio": ("pergunta.wav", WAV, "audio/wav")}
    )
    transcricao = cliente.get(upload.json()["consultar_em"]).json()
    texto = transcricao["texto"]
    assert transcricao["interacao_id"] == repositorio.interacoes[0].id
    assert executor.chamadas == [(texto, "consultar_status_projeto")]
    assert len(repositorio.interacoes) == 1
    assert repositorio.interacoes[0].canal is Canal.VOZ
