"""Testes de integração para a API de upload de áudio."""

from io import BytesIO

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """Cliente de teste para a API."""
    return TestClient(app)


class TestUploadAudio:
    """Testes para o endpoint POST /voz/audios."""

    def test_upload_sem_arquivo(self, client):
        """Deve retornar 400 quando campo audio não é fornecido."""
        response = client.post(
            "/voz/audios",
            data={"idioma": "pt-BR"},
        )

        assert response.status_code == 400
        assert "Campo 'audio' é obrigatório" in response.json()["detail"]

    def test_upload_arquivo_mp3_valido(self, client):
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
        assert "Extensão não suportada" in response.json()["detail"]

    def test_upload_formato_invalido_magic_bytes(self, client):
        """Deve retornar 415 para magic bytes inválidos."""
        # Arquivo com extensão .mp3 mas magic bytes inválidos
        arquivo_falso = BytesIO(b"FAKE" + b"\x00" * 100)

        response = client.post(
            "/voz/audios",
            files={"audio": ("teste.mp3", arquivo_falso, "audio/mpeg")},
        )

        assert response.status_code == 415
        assert "Formato de arquivo não reconhecido" in response.json()["detail"]

    def test_upload_sem_auth(self, client):
        """Deve falhar sem autenticação (quando implementado)."""
        # TODO: Quando autenticação estiver implementada, este teste
        # deve verificar que retorna 401 ou 403
        arquivo_mp3 = BytesIO(b"ID3" + b"\x00" * 100)

        response = client.post(
            "/voz/audios",
            files={"audio": ("teste.mp3", arquivo_mp3, "audio/mpeg")},
        )

        # Por enquanto, sem autenticação implementada, pode ser 202
        # Depois deve ser 401/403
        assert response.status_code in [202, 401, 403]


class TestConsultarTranscricao:
    """Testes para o endpoint GET /voz/audios/{id}/transcricao."""

    def test_consultar_transcricao(self, client):
        """Deve retornar estado da transcrição."""
        # Como implementação é TODO, retorna estado esqueletico
        response = client.get("/voz/audios/test-id-123/transcricao")

        assert response.status_code == 200
        data = response.json()
        assert data["id_audio"] == "test-id-123"
        assert data["estado"] == "transcrevendo"

    def test_consultar_transcricao_id_invalido(self, client):
        """Deve retornar 404 para ID não existente (quando implementado)."""
        # TODO: Quando implementação real estiver pronta,
        # deve retornar 404 para ID inexistente
        response = client.get("/voz/audios/id-inexistente/transcricao")

        # Por retorna 200 com estado esqueletico
        assert response.status_code == 200
