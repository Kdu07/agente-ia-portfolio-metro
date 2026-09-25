"""Persiste submissoes de audio e seu vinculo ao pipeline.

Revision ID: 20260925_audio_persistente
Revises: 20260925_avisos_portfolio
Create Date: 2026-09-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260925_audio_persistente"
down_revision: str | None = "20260925_avisos_portfolio"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "transcricao_audio",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("usuario_id", sa.Text(), nullable=False),
        sa.Column("estado", sa.Text(), nullable=False),
        sa.Column("formato", sa.Text(), nullable=False),
        sa.Column("duracao_segundos", sa.Float(), nullable=False),
        sa.Column("criada_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expira_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("conversa_id", sa.Text(), nullable=True),
        sa.Column("interacao_id", sa.Text(), nullable=True),
        sa.Column("texto", sa.Text(), nullable=True),
        sa.Column("idioma", sa.Text(), nullable=True),
        sa.Column("confianca", sa.Float(), nullable=True),
        sa.Column("latencia_ms", sa.Integer(), nullable=True),
        sa.Column("mensagem_erro", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "estado IN ('recebido', 'transcrevendo', 'concluida', 'falhou')",
            name="ck_transcricao_audio_estado",
        ),
        sa.ForeignKeyConstraint(
            ["usuario_id"],
            ["usuario.id"],
            name="fk_transcricao_audio_usuario_id_usuario",
            ondelete="RESTRICT",
            onupdate="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["conversa_id"],
            ["conversa.id"],
            name="fk_transcricao_audio_conversa_id_conversa",
            ondelete="RESTRICT",
            onupdate="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["interacao_id"],
            ["interacao.id"],
            name="fk_transcricao_audio_interacao_id_interacao",
            ondelete="RESTRICT",
            onupdate="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_transcricao_audio"),
        sa.UniqueConstraint("interacao_id", name="uq_transcricao_audio_interacao_id"),
    )
    op.create_index(
        "ix_transcricao_audio_usuario_criada",
        "transcricao_audio",
        ["usuario_id", sa.text("criada_em DESC")],
    )
    op.create_index(
        "ix_transcricao_audio_expira_em",
        "transcricao_audio",
        ["expira_em"],
    )


def downgrade() -> None:
    op.drop_index("ix_transcricao_audio_expira_em", table_name="transcricao_audio")
    op.drop_index("ix_transcricao_audio_usuario_criada", table_name="transcricao_audio")
    op.drop_table("transcricao_audio")
