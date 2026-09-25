"""Contrato comum dos eventos publicados pelo sistema de mensageria."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class MensagemEvento(BaseModel):
    """Envelope versionado para publicação e consumo de eventos."""

    model_config = ConfigDict(extra="forbid")

    message_id: UUID
    event_type: str = Field(min_length=1, max_length=120)
    schema_version: int = Field(default=1, ge=1)
    occurred_at: datetime
    correlation_id: UUID
    producer: str = Field(min_length=1, max_length=80)
    payload: dict[str, Any]

    @field_validator("occurred_at")
    @classmethod
    def validar_data_utc(cls, value: datetime) -> datetime:
        """Exige data com fuso para evitar eventos sem referência temporal."""
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("occurred_at deve conter fuso horário")
        return value.astimezone(UTC)