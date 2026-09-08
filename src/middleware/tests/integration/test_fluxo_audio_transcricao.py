"""Integração do upload até a consulta da transcrição."""

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


def test_fluxo_completo_do_upload_ate_transcricao(tmp_path, monkeypatch) -> None:
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
            files={"audio": ("pergunta.wav", b"RIFF" + b"\x00" * 100, "audio/wav")},
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
    assert not chamadas[0][0].exists()


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
