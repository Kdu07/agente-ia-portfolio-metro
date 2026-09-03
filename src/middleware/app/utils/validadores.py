"""Validadores de formato de arquivo.

Funções para verificar o formato real de arquivos de áudio através de
magic bytes, evitando uploads maliciosos disfarçados com extensão falsa.
"""

from typing import BinaryIO


# Magic bytes de formatos de áudio comuns
MAGIC_BYTES = {
    b"ID3": "mp3",  # MP3 com tag ID3
    b"\xFF\xFB": "mp3",  # MP3 sem tag ID3 (MPEG Layer 3)
    b"\xFF\xFA": "mp3",  # MP3 variante
    b"\xFF\xE3": "mp3",  # MP3 variante
    b"RIFF": "wav",  # WAV (Waveform Audio File Format)
    b"OggS": "ogg",  # OGG (contêiner Opus/Vorbis)
    b"\x00\x00\x00": "mp4",  # MP4 (aviso: precisa de verificação adicional)
}

# Limites de tamanho em bytes
TAMANHO_MAXIMO_AUDIO = 25 * 1024 * 1024  # 25 MB conforme projeto.md 5.7.3.6


def validar_formato_audio(arquivo: BinaryIO) -> str:
    """Verifica o formato real do arquivo de áudio através de magic bytes.

    Args:
        arquivo: Arquivo binário para verificar

    Returns:
        str: Formato detectado (mp3, wav, ogg, mp4)

    Raises:
        ValueError: Se o formato não for reconhecido ou não for suportado
    """
    # Salva posição atual
    posicao_original = arquivo.tell()
    arquivo.seek(0)

    # Lê primeiros bytes para detecção
    header = arquivo.read(12)

    # Restaura posição
    arquivo.seek(posicao_original)

    # Verifica magic bytes conhecidos
    for magic, formato in MAGIC_BYTES.items():
        if header.startswith(magic):
            # Para MP4, precisa de verificação adicional
            if formato == "mp4":
                if b"ftyp" in header[4:12]:
                    return formato
            else:
                return formato

    raise ValueError(
        "Formato de arquivo não reconhecido. "
        "Formatos aceitos: mp3, wav, ogg, webm, mp4"
    )


def validar_tamanho_arquivo(tamanho: int) -> None:
    """Valida se o tamanho do arquivo está dentro do limite permitido.

    Args:
        tamanho: Tamanho do arquivo em bytes

    Raises:
        ValueError: Se o tamanho exceder o limite máximo
    """
    if tamanho > TAMANHO_MAXIMO_AUDIO:
        raise ValueError(
            f"Arquivo muito grande. Tamanho máximo: {TAMANHO_MAXIMO_AUDIO / (1024*1024):.0f} MB"
        )


def validar_extensao_audio(nome_arquivo: str) -> str:
    """Valida se a extensão do arquivo é aceita.

    Args:
        nome_arquivo: Nome do arquivo com extensão

    Returns:
        str: Extensão em minúsculas (sem ponto)

    Raises:
        ValueError: Se a extensão não for suportada
    """
    extensoes_suportadas = {".mp3", ".wav", ".ogg", ".webm", ".mp4"}
    extensao = nome_arquivo.lower().split(".")[-1] if "." in nome_arquivo else ""

    if f".{extensao}" not in extensoes_suportadas:
        raise ValueError(
            f"Extensão não suportada: .{extensao}. "
            f"Extensões aceitas: {', '.join(extensoes_suportadas)}"
        )

    return extensao
