"""Casos TF-RF02-01 a TF-RF02-07 — interação por texto e voz."""

import pytest
from fastapi.testclient import TestClient

from app.api import deps
from app.api.routes import voz
from app.config import settings
from app.main import app
from app.persistence.models import Canal
from app.pipeline.desfechos import Desfecho
from app.pipeline.orquestrador import Orquestrador
from app.schemas.usuario import Perfil, UsuarioAutenticado
from app.servicos.audio_service import AudioService
from app.voz.transcricao import ErroTranscricao, ResultadoTranscricao

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
    monkeypatch.setattr(voz, "transcrever_arquivo", transcrever)
    app.dependency_overrides[deps.obter_usuario_atual] = lambda: USUARIO
    app.dependency_overrides[deps.obter_orquestrador] = lambda: Orquestrador(
        executor_espiao, repositorio_memoria, repositorio_memoria
    )
    try:
        with TestClient(app) as cliente:
            yield cliente, executor_espiao, repositorio_memoria
    finally:
        app.dependency_overrides.clear()


def test_tf_rf02_01_entrada_por_texto(ambiente) -> None:
    cliente, _, repositorio = ambiente
    resposta = cliente.post("/chat", json={"mensagem": "Status do Projeto Verde"})
    assert resposta.status_code == 200
    assert resposta.json()["desfecho"] == Desfecho.ENCAMINHADA.value
    assert repositorio.interacoes[0].canal is Canal.CHAT


def test_tf_rf02_02_audio_percorre_upload_e_transcricao(ambiente) -> None:
    cliente, _, _ = ambiente
    upload = cliente.post(
        "/voz/audios", files={"audio": ("pergunta.wav", WAV, "audio/wav")}
    )
    consulta = cliente.get(upload.json()["consultar_em"])
    assert upload.status_code == 202
    assert consulta.status_code == 200
    assert consulta.json()["estado"] == "concluida"
    assert consulta.json()["texto"] == "Qual o status do Projeto Verde?"


def test_tf_rf02_03_formato_fora_dos_aceitos(ambiente) -> None:
    cliente, _, _ = ambiente
    resposta = cliente.post(
        "/voz/audios", files={"audio": ("arquivo.exe", b"MZpayload", "application/octet-stream")}
    )
    assert resposta.status_code == 415


@pytest.mark.xfail(strict=True, reason="duração ainda não é calculada antes da aceitação")
def test_tf_rf02_04_audio_acima_de_cinco_minutos_e_recusado(ambiente) -> None:
    cliente, _, _ = ambiente
    resposta = cliente.post(
        "/voz/audios", files={"audio": ("longo.wav", WAV, "audio/wav")}
    )
    assert resposta.status_code == 400
    assert resposta.json()["codigo"] == "AUDIO_MUITO_LONGO"


@pytest.mark.xfail(strict=True, reason="catálogo estruturado de erros de áudio não implementado")
def test_tf_rf02_05_arquivo_ilegivel_e_recusado_antes_do_stt(ambiente) -> None:
    cliente, _, _ = ambiente
    resposta = cliente.post(
        "/voz/audios", files={"audio": ("corrompido.wav", b"RIFF", "audio/wav")}
    )
    assert resposta.status_code == 400
    assert resposta.json()["codigo"] == "AUDIO_ILEGIVEL"


def test_tf_rf02_06_audio_sem_fala_termina_no_estado_falhou(
    ambiente, monkeypatch
) -> None:
    cliente, _, _ = ambiente

    async def sem_fala(caminho, *, idioma):
        raise ErroTranscricao("FALA_NAO_RECONHECIDA", "Nenhuma fala reconhecida")

    monkeypatch.setattr(voz, "transcrever_arquivo", sem_fala)
    upload = cliente.post(
        "/voz/audios", files={"audio": ("silencio.wav", WAV, "audio/wav")}
    )
    consulta = cliente.get(upload.json()["consultar_em"])
    assert consulta.status_code == 200
    assert consulta.json()["estado"] == "falhou"
    assert consulta.json()["mensagem_erro"] == "Nenhuma fala reconhecida"


def test_tf_rf02_07_texto_transcrito_reentra_no_pipeline_como_voz(ambiente) -> None:
    cliente, executor, repositorio = ambiente
    upload = cliente.post(
        "/voz/audios", files={"audio": ("pergunta.wav", WAV, "audio/wav")}
    )
    texto = cliente.get(upload.json()["consultar_em"]).json()["texto"]
    resposta = cliente.post("/chat", json={"mensagem": texto, "canal": "voz"})
    assert resposta.status_code == 200
    assert executor.chamadas == [(texto, "consultar_status_projeto")]
    assert len(repositorio.interacoes) == 1
    assert repositorio.interacoes[0].canal is Canal.VOZ
