"""Testes unitários para o serviço de processamento de áudio."""

from io import BytesIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.servicos.audio_service import AudioService, AudioProcessingError


class TestAudioService:
    """Testes para AudioService."""

    @pytest.fixture
    def audio_service(self, tmp_path):
        """Cria instância do serviço com diretório temporário."""
        with patch("app.servicos.audio_service.settings") as mock_settings:
            mock_settings.BASE_DIR = tmp_path
            return AudioService()

    def test_salvar_arquivo_sucesso(self, audio_service, tmp_path):
        """Deve salvar arquivo com sucesso."""
        arquivo = BytesIO(b"conteudo do audio")
        id_audio = "test-id-123"
        formato = "mp3"

        caminho = audio_service.salvar_arquivo(arquivo, id_audio, formato)

        assert caminho.exists()
        assert caminho.name == f"{id_audio}.{formato}"
        assert caminho.read_bytes() == b"conteudo do audio"

    def test_salvar_arquivo_cria_diretorio(self, tmp_path):
        """Deve criar diretório se não existir."""
        with patch("app.servicos.audio_service.settings") as mock_settings:
            mock_settings.BASE_DIR = tmp_path / "nao_existe"
            service = AudioService()

            arquivo = BytesIO(b"conteudo")
            service.salvar_arquivo(arquivo, "id-123", "wav")

            assert service.diretorio_audio.exists()

    def test_salvar_arquivo_sobrescreve(self, audio_service):
        """Deve sobrescrever arquivo se já existir."""
        arquivo1 = BytesIO(b"conteudo original")
        arquivo2 = BytesIO(b"conteudo novo")
        id_audio = "test-id-123"

        audio_service.salvar_arquivo(arquivo1, id_audio, "mp3")
        audio_service.salvar_arquivo(arquivo2, id_audio, "mp3")

        caminho = audio_service.obter_caminho_arquivo(id_audio, "mp3")
        assert caminho.read_bytes() == b"conteudo novo"

    def test_gerar_id_audio_unico(self, audio_service):
        """Deve gerar IDs únicos."""
        id1 = audio_service.gerar_id_audio()
        id2 = audio_service.gerar_id_audio()

        assert id1 != id2
        assert isinstance(id1, str)
        assert isinstance(id2, str)

    def test_calcular_expiracao_retorna_datetime(self, audio_service):
        """Deve retornar datetime futuro."""
        expiracao = audio_service.calcular_expiracao(10.0)

        from datetime import datetime
        assert isinstance(expiracao, datetime)
        assert expiracao > datetime.utcnow()

    def test_limpar_arquivo_existente(self, audio_service):
        """Deve remover arquivo existente."""
        arquivo = BytesIO(b"conteudo")
        id_audio = "test-id-123"
        caminho = audio_service.salvar_arquivo(arquivo, id_audio, "mp3")

        audio_service.limpar_arquivo(caminho)

        assert not caminho.exists()

    def test_limpar_arquivo_inexistente(self, audio_service):
        """Deve falhar silenciosamente se arquivo não existe."""
        caminho = Path("/caminho/nao/existe/arquivo.mp3")

        # Não deve levantar exceção
        audio_service.limpar_arquivo(caminho)

    def test_obter_caminho_arquivo(self, audio_service):
        """Deve retornar caminho correto."""
        id_audio = "test-id-123"
        formato = "wav"

        caminho = audio_service.obter_caminho_arquivo(id_audio, formato)

        assert caminho.name == f"{id_audio}.{formato}"
        assert caminho.parent == audio_service.diretorio_audio

    def test_obter_caminho_arquivo_nao_cria(self, audio_service):
        """Obter caminho não deve criar o arquivo."""
        id_audio = "test-id-999"
        formato = "ogg"

        caminho = audio_service.obter_caminho_arquivo(id_audio, formato)

        assert not caminho.exists()
