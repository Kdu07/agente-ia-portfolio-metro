"""Validacao estrutural e de duracao feita antes da transcricao."""

import json
from types import SimpleNamespace

import pytest

from app.voz import midia


def _resultado(*, streams, duracao="12.5", retorno=0):
    return SimpleNamespace(
        returncode=retorno,
        stdout=json.dumps({"streams": streams, "format": {"duration": duracao}}),
    )


def test_inspeciona_audio_e_devolve_duracao(monkeypatch, tmp_path) -> None:
    arquivo = tmp_path / "fala.webm"
    arquivo.write_bytes(b"conteudo")
    monkeypatch.setattr(
        midia.subprocess,
        "run",
        lambda *args, **kwargs: _resultado(streams=[{"codec_type": "audio"}]),
    )

    resultado = midia.inspecionar_audio(arquivo)

    assert resultado.duracao_segundos == 12.5


@pytest.mark.parametrize(
    "streams",
    [
        [{"codec_type": "video"}],
        [{"codec_type": "audio"}, {"codec_type": "video"}],
        [],
    ],
)
def test_rejeita_midia_sem_audio_exclusivo(monkeypatch, tmp_path, streams) -> None:
    arquivo = tmp_path / "midia.mp4"
    arquivo.write_bytes(b"conteudo")
    monkeypatch.setattr(
        midia.subprocess,
        "run",
        lambda *args, **kwargs: _resultado(streams=streams),
    )

    with pytest.raises(midia.ErroMidia):
        midia.inspecionar_audio(arquivo)


def test_rejeita_audio_acima_de_cinco_minutos() -> None:
    with pytest.raises(midia.ErroMidia, match="limite"):
        midia.validar_duracao(300.01)


def test_informa_ffprobe_ausente(monkeypatch, tmp_path) -> None:
    arquivo = tmp_path / "fala.wav"
    arquivo.write_bytes(b"conteudo")

    def ausente(*args, **kwargs):
        raise FileNotFoundError

    monkeypatch.setattr(midia.subprocess, "run", ausente)
    with pytest.raises(midia.InspecaoMidiaIndisponivel, match="ffprobe"):
        midia.inspecionar_audio(arquivo)
