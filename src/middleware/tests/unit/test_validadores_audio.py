"""Testes unitários para validadores de formato de áudio."""

import io
from io import BytesIO

import pytest

from app.utils.validadores import (
    validar_extensao_audio,
    validar_formato_audio,
    validar_tamanho_arquivo,
)


class TestValidarExtensaoAudio:
    """Testes para validação de extensão de arquivo."""

    def test_extensao_mp3_valida(self):
        """Deve aceitar extensão .mp3."""
        assert validar_extensao_audio("audio.mp3") == "mp3"

    def test_extensao_wav_valida(self):
        """Deve aceitar extensão .wav."""
        assert validar_extensao_audio("audio.wav") == "wav"

    def test_extensao_ogg_valida(self):
        """Deve aceitar extensão .ogg."""
        assert validar_extensao_audio("audio.ogg") == "ogg"

    def test_extensao_webm_valida(self):
        """Deve aceitar extensão .webm."""
        assert validar_extensao_audio("audio.webm") == "webm"

    def test_extensao_mp4_valida(self):
        """Deve aceitar extensão .mp4."""
        assert validar_extensao_audio("audio.mp4") == "mp4"

    def test_extensao_maiuscula(self):
        """Deve aceitar extensão em maiúsculas."""
        assert validar_extensao_audio("audio.MP3") == "mp3"

    def test_extensao_invalida(self):
        """Deve rejeitar extensão não suportada."""
        with pytest.raises(ValueError, match="Extensão não suportada"):
            validar_extensao_audio("audio.exe")

    def test_extensao_txt_invalida(self):
        """Deve rejeitar extensão .txt."""
        with pytest.raises(ValueError, match="Extensão não suportada"):
            validar_extensao_audio("audio.txt")

    def test_sem_extensao(self):
        """Deve rejeitar arquivo sem extensão."""
        with pytest.raises(ValueError, match="Extensão não suportada"):
            validar_extensao_audio("audio")


class TestValidarTamanhoArquivo:
    """Testes para validação de tamanho de arquivo."""

    def test_tamanho_valido_pequeno(self):
        """Deve aceitar arquivo pequeno."""
        validar_tamanho_arquivo(1024)  # 1 KB

    def test_tamanho_valido_medio(self):
        """Deve aceitar arquivo de tamanho médio."""
        validar_tamanho_arquivo(10 * 1024 * 1024)  # 10 MB

    def test_tamanho_valido_limite(self):
        """Deve aceitar arquivo no limite (25 MB)."""
        validar_tamanho_arquivo(25 * 1024 * 1024)

    def test_tamanho_invalido_excede(self):
        """Deve rejeitar arquivo que excede 25 MB."""
        with pytest.raises(ValueError, match="Arquivo muito grande"):
            validar_tamanho_arquivo(26 * 1024 * 1024)  # 26 MB

    def test_tamanho_zero(self):
        """Deve aceitar arquivo vazio."""
        validar_tamanho_arquivo(0)


class TestValidarFormatoAudio:
    """Testes para validação de formato via magic bytes."""

    def test_mp3_com_id3(self):
        """Deve detectar MP3 com tag ID3."""
        arquivo = BytesIO(b"ID3" + b"\x00" * 20)
        assert validar_formato_audio(arquivo) == "mp3"

    def test_mp3_sem_id3(self):
        """Deve detectar MP3 sem tag ID3."""
        arquivo = BytesIO(b"\xFF\xFB" + b"\x00" * 20)
        assert validar_formato_audio(arquivo) == "mp3"

    def test_wav(self):
        """Deve detectar WAV."""
        arquivo = BytesIO(b"RIFF" + b"\x00" * 20)
        assert validar_formato_audio(arquivo) == "wav"

    def test_ogg(self):
        """Deve detectar OGG."""
        arquivo = BytesIO(b"OggS" + b"\x00" * 20)
        assert validar_formato_audio(arquivo) == "ogg"

    def test_formato_invalido(self):
        """Deve rejeitar formato não reconhecido."""
        arquivo = BytesIO(b"FAKE" + b"\x00" * 20)
        with pytest.raises(ValueError, match="Formato de arquivo não reconhecido"):
            validar_formato_audio(arquivo)

    def test_arquivo_vazio(self):
        """Deve rejeitar arquivo vazio."""
        arquivo = BytesIO(b"")
        with pytest.raises(ValueError, match="Formato de arquivo não reconhecido"):
            validar_formato_audio(arquivo)

    def test_restaura_posicao_arquivo(self):
        """Deve restaurar a posição do arquivo após leitura."""
        arquivo = BytesIO(b"ID3" + b"\x00" * 20)
        arquivo.seek(5)
        posicao_antes = arquivo.tell()
        validar_formato_audio(arquivo)
        assert arquivo.tell() == posicao_antes
