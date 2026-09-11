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


def _ler_vint(dados: bytes, pos: int, *, tamanho: bool) -> tuple[int, int]:
    """Lê um ID ou tamanho EBML delimitado (RFC 8794)."""
    if pos >= len(dados) or dados[pos] == 0:
        raise ValueError("VINT ausente ou inválido")
    largura = 9 - dados[pos].bit_length()
    if largura > (8 if tamanho else 4) or pos + largura > len(dados):
        raise ValueError("VINT truncado ou longo demais")
    valor = int.from_bytes(dados[pos : pos + largura], "big")
    if tamanho:
        mascara = (1 << (7 * largura)) - 1
        valor &= mascara
        if valor == mascara:
            raise ValueError("Tamanho indefinido no cabeçalho")
    return valor, pos + largura


def _eh_webm(header: bytes) -> bool:
    """Identifica DocType webm, sem validar trilhas, codecs ou decodificação."""
    if not header.startswith(b"\x1a\x45\xdf\xa3"):
        return False
    try:
        tamanho, pos = _ler_vint(header, 4, tamanho=True)
        fim = pos + tamanho
        if fim > len(header):
            return False
        dados = header[:fim]
        doctype = None
        while pos < fim:
            elemento, pos = _ler_vint(dados, pos, tamanho=False)
            tamanho, pos = _ler_vint(dados, pos, tamanho=True)
            if pos + tamanho > fim:
                return False
            if elemento == 0x4282:  # DocType; EBML também é usado por Matroska.
                if doctype is not None:
                    return False
                doctype = dados[pos : pos + tamanho].rstrip(b"\x00")
            pos += tamanho
        return doctype == b"webm"
    except ValueError:
        return False


def validar_formato_audio(arquivo: BinaryIO) -> str:
    """Verifica o formato real do arquivo de áudio através de magic bytes.

    Args:
        arquivo: Arquivo binário para verificar

    Returns:
        str: Formato detectado (mp3, wav, ogg, webm, mp4)

    Raises:
        ValueError: Se o formato não for reconhecido ou não for suportado
    """
    # Salva posição atual
    posicao_original = arquivo.tell()
    try:
        arquivo.seek(0)
        # Inspeção limitada: cabeçalhos EBML maiores que 4 KiB são rejeitados.
        header = arquivo.read(4096)
    finally:
        arquivo.seek(posicao_original)

    if _eh_webm(header):
        return "webm"

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
