"""Testes da configuração isolada do Azure Speech."""

from types import SimpleNamespace

import pytest

from app.voz.speech import (
    ErroConfiguracaoSpeech,
    ErroReconhecimentoSpeech,
    reconhecer_arquivo_wav,
)


class _Futuro:
    def __init__(self, resultado) -> None:
        self._resultado = resultado

    def get(self):
        return self._resultado


def _sdk_falso(*, motivo: str, texto: str = ""):
    resultado = SimpleNamespace(reason=motivo, text=texto)

    class SpeechConfig:
        def __init__(self, *, subscription: str, region: str) -> None:
            self.subscription = subscription
            self.region = region
            self.speech_recognition_language = ""

    class AudioConfig:
        def __init__(self, *, filename: str) -> None:
            self.filename = filename

    class SpeechRecognizer:
        def __init__(self, *, speech_config, audio_config) -> None:
            self.speech_config = speech_config
            self.audio_config = audio_config

        def recognize_once_async(self):
            return _Futuro(resultado)

    return SimpleNamespace(
        SpeechConfig=SpeechConfig,
        SpeechRecognizer=SpeechRecognizer,
        audio=SimpleNamespace(AudioConfig=AudioConfig),
        ResultReason=SimpleNamespace(
            RecognizedSpeech="reconhecida",
            NoMatch="sem_correspondencia",
            Canceled="cancelada",
        ),
    )


def test_reconhece_wav_com_configuracao_explicita(tmp_path) -> None:
    arquivo = tmp_path / "fala.wav"
    arquivo.write_bytes(b"RIFF-audio-de-teste")
    sdk = _sdk_falso(motivo="reconhecida", texto="  Qual o status do projeto?  ")

    resultado = reconhecer_arquivo_wav(
        arquivo,
        chave="chave-de-teste",
        regiao="brazilsouth",
        idioma="pt-BR",
        _speechsdk=sdk,
    )

    assert resultado.texto == "Qual o status do projeto?"
    assert resultado.idioma == "pt-BR"


def test_recusa_execucao_sem_chave(tmp_path) -> None:
    arquivo = tmp_path / "fala.wav"
    arquivo.write_bytes(b"RIFF-audio-de-teste")

    with pytest.raises(ErroConfiguracaoSpeech, match="SPEECH_KEY"):
        reconhecer_arquivo_wav(arquivo, chave="", regiao="brazilsouth")


def test_recusa_formato_fora_do_escopo_do_smoke_test(tmp_path) -> None:
    arquivo = tmp_path / "fala.mp3"
    arquivo.write_bytes(b"ID3-audio-de-teste")

    with pytest.raises(ErroConfiguracaoSpeech, match="apenas arquivo WAV"):
        reconhecer_arquivo_wav(arquivo, chave="chave", regiao="brazilsouth")


def test_informa_quando_nenhuma_fala_e_reconhecida(tmp_path) -> None:
    arquivo = tmp_path / "silencio.wav"
    arquivo.write_bytes(b"RIFF-audio-de-teste")
    sdk = _sdk_falso(motivo="sem_correspondencia")

    with pytest.raises(ErroReconhecimentoSpeech, match="Nenhuma fala"):
        reconhecer_arquivo_wav(
            arquivo,
            chave="chave",
            regiao="brazilsouth",
            _speechsdk=sdk,
        )
