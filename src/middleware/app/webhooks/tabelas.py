"""Esquema `webhook`: canais do Drive, recebimentos e cursor das fontes.

Registros que a seção 9.1.2.7.1 do Projeto.md aponta como necessários e
ainda inexistentes. Schema próprio pela mesma razão do `rag`: deixar
visível que é o registro de entrada de sistemas externos, e não o
registro operacional das conversas.

- `webhook.canal_drive`: uma inscrição `changes.watch`. Guarda o hash
  SHA-256 do token, nunca o token: quem lê o banco não consegue forjar
  uma notificação;
- `webhook.recebimento`: uma notificação aceita, com a chave externa
  única por provedor e os UUIDs do evento interno. É a chave que torna a
  repetição idempotente, e `publicado_em` vazio é o que a recuperação de
  pendentes procura;
- `webhook.sincronizacao_fonte`: o cursor de mudanças confirmado de cada
  fonte. O cursor vem do servidor, nunca de um callback;
- `webhook.fonte_portfolio`: o emissor do WH-02 (seção 9.1.2.7.2), com a
  planilha, os projetos e os tipos de evento que ele pode alterar.

O recebimento serve aos dois webhooks: a chave externa do Drive é
`canal:número da mensagem`, e a do Apps Script é `source_id:event_id`,
acompanhada do hash do corpo.
"""

from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.persistence.tabelas import Base, _valores
from app.webhooks.modelos import (
    EstadoCanal,
    EstadoSincronizacao,
    FontePortfolio,
    Provedor,
    Recebimento,
    TipoEventoPortfolio,
)

ESQUEMA = "webhook"


class CanalDriveTabela(Base):
    """Inscrição `changes.watch` de uma fonte do Drive."""

    __tablename__ = "canal_drive"

    # UUID gerado pela aplicação e enviado ao Google como `id` do canal.
    canal_id: Mapped[str] = mapped_column(Text, primary_key=True)
    fonte_id: Mapped[str] = mapped_column(Text, nullable=False)
    token_sha256: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    # Confirmados pela resposta autenticada da inscrição; nulos enquanto
    # pendente. Um recurso visto só num callback nunca é gravado aqui.
    recurso_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    recurso_uri: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Enquanto pendente, prazo local da inscrição; depois, a expiração
    # concedida pelo Google.
    expira_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    estado: Mapped[str] = mapped_column(Text, nullable=False)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ativado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    encerrado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint(f"estado IN ({_valores(EstadoCanal)})", name="estado"),
        CheckConstraint("octet_length(token_sha256) = 32", name="token_sha256"),
        CheckConstraint(
            "estado <> 'ativo' OR (recurso_id IS NOT NULL AND recurso_uri IS NOT NULL)",
            name="recurso_confirmado",
        ),
        Index("ix_canal_drive_fonte_estado", "fonte_id", "estado"),
        {"schema": ESQUEMA},
    )


class RecebimentoTabela(Base):
    """Notificação aceita e o evento interno que ela originou."""

    __tablename__ = "recebimento"

    message_id: Mapped[str] = mapped_column(Text, primary_key=True)
    correlation_id: Mapped[str] = mapped_column(Text, nullable=False)
    provedor: Mapped[str] = mapped_column(Text, nullable=False)
    chave_externa: Mapped[str] = mapped_column(Text, nullable=False)
    fonte_id: Mapped[str] = mapped_column(Text, nullable=False)
    # Canais são preservados enquanto houver recebimento retido.
    canal_id: Mapped[str | None] = mapped_column(
        Text,
        ForeignKey(f"{ESQUEMA}.canal_drive.canal_id", ondelete="RESTRICT"),
        nullable=True,
    )
    # O payload normalizado do evento interno; nunca o token, a URI
    # recebida ou conteúdo de documento.
    evento: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    recebido_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    publicado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    processado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    tentativas: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    # Código da falha, sem conteúdo sensível.
    erro_codigo: Mapped[str | None] = mapped_column(Text, nullable=True)
    # SHA-256 dos bytes exatos do corpo, só no WH-02.
    corpo_sha256: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)

    __table_args__ = (
        CheckConstraint(f"provedor IN ({_valores(Provedor)})", name="provedor"),
        CheckConstraint("tentativas >= 0", name="tentativas"),
        CheckConstraint(
            "corpo_sha256 IS NULL OR octet_length(corpo_sha256) = 32", name="corpo_sha256"
        ),
        UniqueConstraint("provedor", "chave_externa", name="uq_recebimento_chave_externa"),
        # A recuperação procura só o que ainda não foi publicado.
        Index(
            "ix_recebimento_pendente",
            "recebido_em",
            postgresql_where=text("publicado_em IS NULL"),
        ),
        {"schema": ESQUEMA},
    )

    def to_dominio(self) -> Recebimento:
        return Recebimento(
            message_id=self.message_id,
            correlation_id=self.correlation_id,
            provedor=Provedor(self.provedor),
            chave_externa=self.chave_externa,
            fonte_id=self.fonte_id,
            canal_id=self.canal_id,
            evento=dict(self.evento),
            recebido_em=self.recebido_em,
            publicado_em=self.publicado_em,
            processado_em=self.processado_em,
            tentativas=self.tentativas,
            erro_codigo=self.erro_codigo,
            corpo_sha256=None if self.corpo_sha256 is None else bytes(self.corpo_sha256),
        )


class SincronizacaoFonteTabela(Base):
    """Cursor de mudanças confirmado de uma fonte documental."""

    __tablename__ = "sincronizacao_fonte"

    fonte_id: Mapped[str] = mapped_column(Text, primary_key=True)
    # `pageToken` do Drive: serve à leitura das mudanças, não é credencial
    # nem chave de deduplicação.
    cursor: Mapped[str | None] = mapped_column(Text, nullable=True)
    estado: Mapped[str] = mapped_column(Text, nullable=False)
    concluida_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    atualizado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        CheckConstraint(f"estado IN ({_valores(EstadoSincronizacao)})", name="estado"),
        {"schema": ESQUEMA},
    )


class FontePortfolioTabela(Base):
    """Emissor do WH-02 e o escopo que ele pode alterar."""

    __tablename__ = "fonte_portfolio"

    # Mesmo formato do cabeçalho `X-Prata-Source` e do cadastro de chaves.
    source_id: Mapped[str] = mapped_column(Text, primary_key=True)
    planilha_id: Mapped[str] = mapped_column(Text, nullable=False)
    projetos: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False)
    tipos: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False)
    ativa: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    criada_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    atualizada_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        CheckConstraint("source_id ~ '^[A-Za-z0-9_-]{1,64}$'", name="source_id"),
        CheckConstraint(f"tipos <@ ARRAY[{_valores(TipoEventoPortfolio)}]::text[]", name="tipos"),
        {"schema": ESQUEMA},
    )

    def to_dominio(self) -> FontePortfolio:
        return FontePortfolio(
            source_id=self.source_id,
            planilha_id=self.planilha_id,
            projetos=frozenset(self.projetos),
            tipos=frozenset(TipoEventoPortfolio(tipo) for tipo in self.tipos),
            ativa=self.ativa,
        )
