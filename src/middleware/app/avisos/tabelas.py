"""Tabelas `preferencia_aviso` e `aviso`, no schema padrão.

Ficam ao lado de `usuario`, e não no schema `webhook`: são dado do
usuário, lido pelas rotas autenticadas, e não registro de entrada de
sistema externo. `projeto_codigo` fica sem chave estrangeira de propósito,
como o `intencao_id` de `interacao`: o portfólio vive noutro metadata, e
o acesso ao projeto é revalidado a cada leitura, não congelado aqui.
"""

from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.avisos.modelos import Aviso, PreferenciaAviso
from app.persistence.tabelas import Base, _valores
from app.webhooks.modelos import TipoEventoPortfolio

_CHECK_TIPO = f"event_type IN ({_valores(TipoEventoPortfolio)})"


class PreferenciaAvisoTabela(Base):
    """Adesão de um usuário aos avisos de um tipo de evento de um projeto."""

    __tablename__ = "preferencia_aviso"

    usuario_id: Mapped[str] = mapped_column(
        Text, ForeignKey("usuario.id", ondelete="CASCADE"), primary_key=True
    )
    projeto_codigo: Mapped[str] = mapped_column(Text, primary_key=True)
    event_type: Mapped[str] = mapped_column(Text, primary_key=True)
    ativa: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    severidade_minima: Mapped[int | None] = mapped_column(Integer, nullable=True)
    atualizada_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        CheckConstraint(_CHECK_TIPO, name="event_type"),
        CheckConstraint(
            "severidade_minima IS NULL OR (event_type = 'risco.alterado' "
            "AND severidade_minima BETWEEN 1 AND 25)",
            name="severidade_minima",
        ),
        Index("ix_preferencia_aviso_candidatas", "projeto_codigo", "event_type"),
    )

    def to_dominio(self) -> PreferenciaAviso:
        return PreferenciaAviso(
            usuario_id=self.usuario_id,
            projeto_codigo=self.projeto_codigo,
            event_type=TipoEventoPortfolio(self.event_type),
            ativa=self.ativa,
            severidade_minima=self.severidade_minima,
            atualizada_em=self.atualizada_em,
        )


class AvisoTabela(Base):
    """Aviso privado de uma alteração no portfólio."""

    __tablename__ = "aviso"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    usuario_id: Mapped[str] = mapped_column(
        Text, ForeignKey("usuario.id", ondelete="CASCADE"), nullable=False
    )
    projeto_codigo: Mapped[str] = mapped_column(Text, nullable=False)
    source_id: Mapped[str] = mapped_column(Text, nullable=False)
    event_id: Mapped[str] = mapped_column(Text, nullable=False)
    event_type: Mapped[str] = mapped_column(Text, nullable=False)
    entity_id: Mapped[str] = mapped_column(Text, nullable=False)
    versao: Mapped[int] = mapped_column(BigInteger, nullable=False)
    diferencas: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    lido_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint(_CHECK_TIPO, name="event_type"),
        # Reentrega do mesmo evento não gera o aviso de novo.
        UniqueConstraint("source_id", "event_id", "usuario_id", name="uq_aviso_evento_usuario"),
        Index("ix_aviso_usuario_criado", "usuario_id", text("criado_em DESC")),
    )

    def to_dominio(self) -> Aviso:
        return Aviso(
            id=self.id,
            usuario_id=self.usuario_id,
            projeto_codigo=self.projeto_codigo,
            event_type=TipoEventoPortfolio(self.event_type),
            entity_id=self.entity_id,
            versao=self.versao,
            diferencas=dict(self.diferencas),
            criado_em=self.criado_em,
            lido_em=self.lido_em,
        )
