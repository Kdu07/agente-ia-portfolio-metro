"""Inspecao estrutural de arquivos de audio com ffprobe.

Magic bytes identificam o conteiner, mas nao provam que ele possui uma
trilha de audio decodificavel. O ffprobe usa os mesmos demuxers do FFmpeg
utilizados em producao e devolve as trilhas e a duracao sem transcrever nem
reproduzir o conteudo.
"""

from __future__ import annotations

import json
import math
import subprocess
from dataclasses import dataclass
from pathlib import Path

from app.config import settings

LIMITE_DURACAO_SEGUNDOS = 300.0


class ErroMidia(ValueError):
    """Arquivo ausente, corrompido ou incompatível com o contrato de voz."""


class InspecaoMidiaIndisponivel(RuntimeError):
    """O servidor nao possui o instrumento necessario para validar a midia."""


class AudioMuitoLongo(ErroMidia):
    """Duracao valida, mas acima do limite contratual."""

    def __init__(self, duracao_segundos: float) -> None:
        self.duracao_segundos = duracao_segundos
        super().__init__(
            f"O audio tem {duracao_segundos:.2f}s; o limite e "
            f"{LIMITE_DURACAO_SEGUNDOS:.0f}s"
        )


@dataclass(frozen=True)
class MidiaAudio:
    """Metadados comprovados antes de consumir a franquia do Speech."""

    duracao_segundos: float


def inspecionar_audio(caminho: str | Path) -> MidiaAudio:
    """Confirma trilha exclusivamente de audio e calcula sua duracao."""
    comando = [
        settings.ffprobe_path,
        "-v",
        "error",
        "-show_entries",
        "format=duration:stream=codec_type",
        "-of",
        "json",
        str(caminho),
    ]
    try:
        resultado = subprocess.run(
            comando,
            capture_output=True,
            text=True,
            timeout=settings.ffprobe_timeout_seconds,
            check=False,
        )
    except FileNotFoundError as erro:
        raise InspecaoMidiaIndisponivel(
            "ffprobe nao encontrado no ambiente do middleware"
        ) from erro
    except subprocess.TimeoutExpired as erro:
        raise ErroMidia("A inspecao do arquivo excedeu o tempo limite") from erro

    if resultado.returncode != 0:
        raise ErroMidia("O arquivo nao pode ser decodificado")
    try:
        payload = json.loads(resultado.stdout)
        tipos = [stream.get("codec_type") for stream in payload.get("streams", [])]
        duracao = float(payload["format"]["duration"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as erro:
        raise ErroMidia("A midia nao informou uma duracao valida") from erro

    if "audio" not in tipos:
        raise ErroMidia("O arquivo nao possui trilha de audio")
    if "video" in tipos:
        raise ErroMidia("Arquivos com trilha de video nao sao aceitos")
    if not math.isfinite(duracao) or duracao <= 0:
        raise ErroMidia("A duracao do audio e invalida")
    return MidiaAudio(duracao_segundos=duracao)


def validar_duracao(duracao_segundos: float) -> None:
    """Recusa audios acima dos cinco minutos definidos no contrato."""
    if duracao_segundos > LIMITE_DURACAO_SEGUNDOS:
        raise AudioMuitoLongo(duracao_segundos)
