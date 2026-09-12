"""Integração do upload até a consulta da transcrição."""

import pytest
from fastapi.testclient import TestClient

from app.api import deps
from app.api.routes import voz
from app.config import settings
from app.main import app
from app.schemas.usuario import Perfil, UsuarioAutenticado
from app.servicos.audio_service import AudioService
from app.voz.transcricao import ErroTranscricao, ResultadoTranscricao

USUARIO = UsuarioAutenticado(
    id="u-audio",
    nome="Usuária de teste",
    perfil=Perfil.LIDER_PROJETO,
)


def _cliente_isolado(tmp_path, monkeypatch, transcrever):
    monkeypatch.setattr(settings, "base_dir", tmp_path)
    monkeypatch.setattr(voz, "audio_service", AudioService())
    monkeypatch.setattr(voz, "transcrever_arquivo", transcrever)
    app.dependency_overrides[deps.obter_usuario_atual] = lambda: USUARIO
    return TestClient(app)


@pytest.mark.parametrize(
    ("nome", "conteudo", "mime"),
    [
        ("pergunta.wav", b"RIFF" + b"\x00" * 100, "audio/wav"),
        ("pergunta.webm", b"\x1a\x45\xdf\xa3\x87\x42\x82\x84webm", "audio/webm"),
    ],
)
def test_fluxo_completo_do_upload_ate_transcricao(
    tmp_path, monkeypatch, nome, conteudo, mime
) -> None:
    chamadas = []

    async def transcrever(caminho, *, idioma):
        chamadas.append((caminho, idioma))
        return ResultadoTranscricao(
            texto="Qual o status do Projeto Verde?",
            idioma="pt-BR",
            confianca=0.94,
            duracao_segundos=1.25,
            latencia_ms=180,
        )

    with _cliente_isolado(tmp_path, monkeypatch, transcrever) as cliente:
        upload = cliente.post(
            "/voz/audios",
            files={"audio": (nome, conteudo, mime)},
            data={"idioma": "pt-BR"},
        )
        assert upload.status_code == 202
        consulta = cliente.get(upload.json()["consultar_em"])

    app.dependency_overrides.clear()
    assert consulta.status_code == 200
    assert consulta.json() == {
        "id_audio": upload.json()["id_audio"],
        "estado": "concluida",
        "texto": "Qual o status do Projeto Verde?",
        "idioma": "pt-BR",
        "confianca": 0.94,
        "duracao_segundos": 1.25,
        "latencia_ms": 180,
        "mensagem_erro": None,
    }
    assert chamadas[0][1] == "pt-BR"
    assert chamadas[0][0].suffix == "." + nome.rsplit(".", 1)[1]
    assert not chamadas[0][0].exists()


def test_upload_matroska_renomeado_webm_retorna_415(tmp_path, monkeypatch) -> None:
    async def transcrever(caminho, *, idioma):
        raise AssertionError("arquivo rejeitado não deve chegar ao STT")

    conteudo = b"\x1a\x45\xdf\xa3\x8b\x42\x82\x88matroska"
    try:
        with _cliente_isolado(tmp_path, monkeypatch, transcrever) as cliente:
            resposta = cliente.post(
                "/voz/audios", files={"audio": ("falso.webm", conteudo, "audio/webm")}
            )
        assert resposta.status_code == 415
    finally:
        app.dependency_overrides.clear()


def test_falha_da_transcricao_fica_disponivel_para_consulta(tmp_path, monkeypatch) -> None:
    async def transcrever(caminho, *, idioma):
        raise ErroTranscricao("FALA_NAO_RECONHECIDA", "Nenhuma fala foi reconhecida no áudio")

    with _cliente_isolado(tmp_path, monkeypatch, transcrever) as cliente:
        upload = cliente.post(
            "/voz/audios",
            files={"audio": ("silencio.wav", b"RIFF" + b"\x00" * 100, "audio/wav")},
        )
        consulta = cliente.get(upload.json()["consultar_em"])

    app.dependency_overrides.clear()
    assert consulta.status_code == 200
    assert consulta.json()["estado"] == "falhou"
    assert consulta.json()["mensagem_erro"] == "Nenhuma fala foi reconhecida no áudio"


def test_consulta_id_desconhecido_retorna_404(tmp_path, monkeypatch) -> None:
    async def transcrever(caminho, *, idioma):
        raise AssertionError("não deveria ser chamado")

    with _cliente_isolado(tmp_path, monkeypatch, transcrever) as cliente:
        resposta = cliente.get("/voz/audios/id-inexistente/transcricao")

    app.dependency_overrides.clear()
    assert resposta.status_code == 404
