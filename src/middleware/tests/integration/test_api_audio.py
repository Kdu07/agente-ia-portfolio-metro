"""Testes de integração para a API de upload de áudio."""

from io import BytesIO
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.api import deps
from app.api.routes import voz
from app.config import settings
from app.main import app
from app.schemas.usuario import Perfil, UsuarioAutenticado
from app.servicos.audio_service import AudioService
from app.voz.midia import MidiaAudio
from app.voz.speech import ErroTokenSpeech, TokenVoz
from app.voz.transcricao import ResultadoTranscricao
from tests.apoio_audio import BancoFalso, ProcessadorAudioFalso, RepositorioAudioMemoria


@pytest.fixture
def ambiente_audio(tmp_path, monkeypatch):
    """Isola arquivos, transcrições e dependências sem acessar Azure ou banco."""
    monkeypatch.setattr(settings, "base_dir", tmp_path)
    monkeypatch.setattr(voz, "audio_service", AudioService())
    monkeypatch.setattr(
        voz,
        "inspecionar_audio",
        lambda _caminho: MidiaAudio(duracao_segundos=1.25),
    )
    transcrever = AsyncMock(
        return_value=ResultadoTranscricao(
            texto="Qual o status do Projeto Verde?",
            idioma="pt-BR",
            confianca=0.94,
            duracao_segundos=1.25,
            latencia_ms=180,
        )
    )
    repositorio = RepositorioAudioMemoria()
    processador = ProcessadorAudioFalso(repositorio, transcrever)
    overrides = app.dependency_overrides.copy()
    overrides.pop(deps.obter_usuario_atual, None)
    # Sem cookie, a dependência real de autenticação retorna 401 antes de usar o banco.
    overrides[deps.obter_sessao] = lambda: BancoFalso()
    overrides[deps.obter_audios] = lambda: repositorio
    overrides[deps.obter_processador_audio] = lambda: processador
    monkeypatch.setattr(app, "dependency_overrides", overrides)
    return transcrever


@pytest.fixture
def client_sem_auth(ambiente_audio):
    """Preserva a verificação real de ausência de cookie."""
    with TestClient(app) as cliente:
        yield cliente


@pytest.fixture
def client(client_sem_auth, monkeypatch):
    """Usuário sintético somente para testar o contrato de áudio autenticado."""
    usuario = UsuarioAutenticado(
        id="u-teste-api-audio", nome="Usuária de teste", perfil=Perfil.LIDER_PROJETO
    )
    monkeypatch.setitem(app.dependency_overrides, deps.obter_usuario_atual, lambda: usuario)
    return client_sem_auth


class TestUploadAudio:
    """Testes para o endpoint POST /voz/audios."""

    def test_upload_sem_arquivo(self, client, ambiente_audio):
        """Deve retornar 422 quando o campo obrigatório audio não é fornecido."""
        response = client.post(
            "/voz/audios",
            data={"idioma": "pt-BR"},
        )

        assert response.status_code == 400
        assert response.json()["codigo"] == "AUDIO_AUSENTE"
        ambiente_audio.assert_not_awaited()

    def test_upload_arquivo_mp3_valido(self, client, ambiente_audio):
        """Deve aceitar arquivo MP3 válido."""
        arquivo_mp3 = BytesIO(b"ID3" + b"\x00" * 100)

        response = client.post(
            "/voz/audios",
            files={"audio": ("teste.mp3", arquivo_mp3, "audio/mpeg")},
            data={"idioma": "pt-BR"},
        )

        assert response.status_code == 202
        data = response.json()
        assert "id_audio" in data
        assert data["estado"] == "recebido"
        assert "consultar_em" in data
        assert "expira_em" in data
        ambiente_audio.assert_awaited_once()
        assert ambiente_audio.await_args.kwargs == {"idioma": "pt-BR"}

    def test_upload_arquivo_wav_valido(self, client):
        """Deve aceitar arquivo WAV válido."""
        arquivo_wav = BytesIO(b"RIFF" + b"\x00" * 100)

        response = client.post(
            "/voz/audios",
            files={"audio": ("teste.wav", arquivo_wav, "audio/wav")},
        )

        assert response.status_code == 202

    def test_upload_arquivo_ogg_valido(self, client):
        """Deve aceitar arquivo OGG válido."""
        arquivo_ogg = BytesIO(b"OggS" + b"\x00" * 100)

        response = client.post(
            "/voz/audios",
            files={"audio": ("teste.ogg", arquivo_ogg, "audio/ogg")},
        )

        assert response.status_code == 202

    def test_upload_extensao_invalida(self, client):
        """Deve retornar 415 para extensão não suportada."""
        arquivo_exe = BytesIO(b"MZ" + b"\x00" * 100)

        response = client.post(
            "/voz/audios",
            files={"audio": ("teste.exe", arquivo_exe, "application/octet-stream")},
        )

        assert response.status_code == 415
        assert response.json()["codigo"] == "AUDIO_FORMATO_NAO_SUPORTADO"

    def test_upload_formato_invalido_magic_bytes(self, client):
        """Deve retornar 415 para magic bytes inválidos."""
        # Arquivo com extensão .mp3 mas magic bytes inválidos
        arquivo_falso = BytesIO(b"FAKE" + b"\x00" * 100)

        response = client.post(
            "/voz/audios",
            files={"audio": ("teste.mp3", arquivo_falso, "audio/mpeg")},
        )

        assert response.status_code == 415
        assert response.json()["codigo"] == "AUDIO_FORMATO_NAO_SUPORTADO"

    def test_upload_sem_auth(self, client_sem_auth, ambiente_audio):
        """Deve retornar 401 sem cookie, mesmo com arquivo de formato aceito."""
        arquivo_mp3 = BytesIO(b"ID3" + b"\x00" * 100)

        response = client_sem_auth.post(
            "/voz/audios",
            files={"audio": ("teste.mp3", arquivo_mp3, "audio/mpeg")},
        )

        assert response.status_code == 401
        assert response.json()["detail"] == "Sessão ausente"
        ambiente_audio.assert_not_awaited()


class TestConsultarTranscricao:
    """Testes para o endpoint GET /voz/audios/{id}/transcricao."""

    def test_consultar_transcricao(self, client):
        """Consulta uma transcrição criada pelo upload com STT simulado."""
        upload = client.post(
            "/voz/audios",
            files={"audio": ("teste.mp3", b"ID3" + b"\x00" * 100, "audio/mpeg")},
        )
        assert upload.status_code == 202
        response = client.get(upload.json()["consultar_em"])

        assert response.status_code == 200
        data = response.json()
        assert data["id_audio"] == upload.json()["id_audio"]
        assert data["estado"] == "concluida"
        assert data["texto"] == "Qual o status do Projeto Verde?"

    def test_consultar_transcricao_id_invalido(self, client):
        """Deve retornar 404 para ID não existente."""
        response = client.get("/voz/audios/id-inexistente/transcricao")

        assert response.status_code == 404

    def test_nao_permite_consultar_audio_de_outro_usuario(self, client, monkeypatch):
        upload = client.post(
            "/voz/audios",
            files={"audio": ("teste.mp3", b"ID3" + b"\x00" * 100, "audio/mpeg")},
        )
        outro = UsuarioAutenticado(
            id="outro-usuario",
            nome="Outra pessoa",
            perfil=Perfil.LIDER_PROJETO,
        )
        monkeypatch.setitem(app.dependency_overrides, deps.obter_usuario_atual, lambda: outro)

        response = client.get(upload.json()["consultar_em"])

        assert response.status_code == 404
        assert response.json()["codigo"] == "AUDIO_NAO_ENCONTRADO"

    def test_consultar_transcricao_sem_auth(self, client_sem_auth, ambiente_audio):
        """A consulta também exige autenticação, antes de procurar o ID."""
        response = client_sem_auth.get("/voz/audios/id-inexistente/transcricao")
        assert response.status_code == 401
        assert response.json()["detail"] == "Sessão ausente"
        ambiente_audio.assert_not_awaited()


class TestTokenVoz:
    def test_emite_token_real_para_usuario_autenticado(self, client, monkeypatch) -> None:
        async def emitir():
            return TokenVoz(
                token="credencial-curta",
                regiao="brazilsouth",
                idioma="pt-BR",
            )

        monkeypatch.setattr(voz, "emitir_token", emitir)

        resposta = client.get("/voz/token")

        assert resposta.status_code == 200
        assert resposta.json() == {
            "token": "credencial-curta",
            "regiao": "brazilsouth",
            "expira_em_segundos": 600,
            "idioma": "pt-BR",
        }

    def test_falha_do_provedor_nao_expoe_detalhe_interno(self, client, monkeypatch) -> None:
        async def falhar():
            raise ErroTokenSpeech("segredo do provedor")

        monkeypatch.setattr(voz, "emitir_token", falhar)

        resposta = client.get("/voz/token")

        assert resposta.status_code == 503
        assert resposta.json()["codigo"] == "SERVICO_INDISPONIVEL"
        assert "segredo" not in resposta.text
