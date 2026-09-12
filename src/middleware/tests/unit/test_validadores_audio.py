"""Testes unitários para validadores de formato de áudio."""

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

    @pytest.mark.parametrize("tamanho", [b"\x87", b"\x40\x07", b"\x01" + b"\x00" * 6 + b"\x07"])
    def test_webm(self, tamanho):
        """Reconhece DocType webm com diferentes larguras de tamanho EBML."""
        arquivo = BytesIO(b"\x1a\x45\xdf\xa3" + tamanho + b"\x42\x82\x84webm")
        assert validar_formato_audio(arquivo) == "webm"

    def test_webm_com_outros_campos_no_cabecalho(self):
        campos = b"\x42\x86\x81\x01\x42\x82\x84webm\x42\x85\x81\x02"
        arquivo = BytesIO(b"\x1a\x45\xdf\xa3\x8f" + campos)
        assert validar_formato_audio(arquivo) == "webm"

    @pytest.mark.parametrize(
        "conteudo",
        [
            b"\x1a\x45\xdf\xa3",  # Só assinatura, sem cabeçalho.
            b"\x1a\x45\xdf\xa3\xff\x42\x82\x84webm",  # Tamanho indefinido.
            b"\x1a\x45\xdf\xa3\x00\x42\x82\x84webm",  # VINT inválido.
            b"\x1a\x45\xdf\xa3\x8b\x42\x82\x88matroska",  # Outro DocType.
            b"\x1a\x45\xdf\xa3\x87\x42\x82\x84web",  # Cabeçalho truncado.
            b"\x1a\x45\xdf\xa3\x87\x42\x82\x88webm",  # Campo excede cabeçalho.
            b"\x1a\x45\xdf\xa3\x84\x42\x86\x81\x01",  # DocType ausente.
            b"\x1a\x45\xdf\xa3\x80\x42\x82\x84webm",  # DocType fora do header.
            b"\x1a\x45\xdf\xa3\x89\xec\x87\x42\x82\x84webm",  # Dentro de Void.
            b"FAKE\x42\x82\x84webm",  # DocType sem assinatura EBML.
            b"\x1a\x45\xdf\xa3\x8e" + b"\x42\x82\x84webm" * 2,  # Duplicado.
            b"\x1a\x45\xdf\xa3\x50\x00" + b"\x00" * 4096,  # Excede inspeção.
        ],
    )
    def test_rejeita_webm_com_cabecalho_invalido(self, conteudo):
        arquivo = BytesIO(conteudo)
        arquivo.seek(2)
        with pytest.raises(ValueError, match="Formato de arquivo não reconhecido"):
            validar_formato_audio(arquivo)
        assert arquivo.tell() == 2

    def test_webm_preserva_posicao_e_limita_leitura(self):
        class LeituraLimitada(BytesIO):
            def read(self, size=-1):
                assert 0 < size <= 4096
                return super().read(size)

        arquivo = LeituraLimitada(b"\x1a\x45\xdf\xa3\x87\x42\x82\x84webm")
        arquivo.seek(5)
        assert validar_formato_audio(arquivo) == "webm"
        assert arquivo.tell() == 5

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
