"""Testes do contrato de eventos da mensageria."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.mensagem import MensagemEvento


def criar_evento(**alteracoes) -> dict:
    evento = {
        "message_id": uuid4(),
        "event_type": "audio.transcription.requested",
        "schema_version": 1,
        "occurred_at": datetime.now(UTC),
        "correlation_id": uuid4(),
        "producer": "middleware",
        "payload": {"id_audio": "audio-1"},
    }
    evento.update(alteracoes)
    return evento


def test_evento_valido_normaliza_data_para_utc():
    evento = MensagemEvento.model_validate(
        criar_evento(occurred_at="2026-01-01T09:00:00-03:00")
    )

    assert evento.occurred_at == datetime(2026, 1, 1, 12, tzinfo=UTC)


def test_evento_rejeita_data_sem_fuso():
    with pytest.raises(ValidationError, match="fuso horário"):
        MensagemEvento.model_validate(criar_evento(occurred_at="2026-01-01T12:00:00"))


def test_evento_rejeita_campo_desconhecido():
    with pytest.raises(ValidationError, match="extra_forbidden"):
        MensagemEvento.model_validate(criar_evento(attempt=1))


def test_evento_pode_ser_serializado_para_json():
    evento = MensagemEvento.model_validate(criar_evento())

    serializado = evento.model_dump_json()

    assert '"event_type":"audio.transcription.requested"' in serializado
    assert '"payload":{"id_audio":"audio-1"}' in serializado