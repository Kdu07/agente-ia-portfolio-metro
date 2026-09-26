"""Cria o schema `webhook` com canais do Drive, recebimentos e cursores.

Registros exigidos pelo contrato do WH-01 (Projeto.md, seção 9.1.2.7.1):
o canal da inscrição `changes.watch`, com o hash do token; o recebimento
de cada notificação, com a chave externa que torna a repetição
idempotente e os UUIDs do evento interno; e o cursor de mudanças de cada
fonte. Ver app/webhooks/tabelas.py.

Escrita à mão contra o metadata: o autogenerate não cria schema nem
índice parcial.

Revision ID: 20260923_webhook_drive
Revises: 20260922_latencia_por_etapa
Create Date: 2026-09-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260923_webhook_drive"
down_revision: str | None = "20260922_latencia_por_etapa"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS webhook")

    op.create_table(
        "canal_drive",
        sa.Column("canal_id", sa.Text(), nullable=False),
        sa.Column("fonte_id", sa.Text(), nullable=False),
        sa.Column("token_sha256", sa.LargeBinary(), nullable=False),
        sa.Column("recurso_id", sa.Text(), nullable=True),
        sa.Column("recurso_uri", sa.Text(), nullable=True),
        sa.Column("expira_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("estado", sa.Text(), nullable=False),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ativado_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("encerrado_em", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "estado IN ('pendente', 'ativo', 'encerrado')", name="ck_canal_drive_estado"
        ),
        sa.CheckConstraint("octet_length(token_sha256) = 32", name="ck_canal_drive_token_sha256"),
        sa.CheckConstraint(
            "estado <> 'ativo' OR (recurso_id IS NOT NULL AND recurso_uri IS NOT NULL)",
            name="ck_canal_drive_recurso_confirmado",
        ),
        sa.PrimaryKeyConstraint("canal_id", name="pk_canal_drive"),
        schema="webhook",
    )
    op.create_index(
        "ix_canal_drive_fonte_estado",
        "canal_drive",
        ["fonte_id", "estado"],
        schema="webhook",
    )

    op.create_table(
        "recebimento",
        sa.Column("message_id", sa.Text(), nullable=False),
        sa.Column("correlation_id", sa.Text(), nullable=False),
        sa.Column("provedor", sa.Text(), nullable=False),
        sa.Column("chave_externa", sa.Text(), nullable=False),
        sa.Column("fonte_id", sa.Text(), nullable=False),
        sa.Column("canal_id", sa.Text(), nullable=True),
        sa.Column("evento", postgresql.JSONB(), nullable=False),
        sa.Column("recebido_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("publicado_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("processado_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("tentativas", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("erro_codigo", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "provedor IN ('google_drive', 'apps_script')", name="ck_recebimento_provedor"
        ),
        sa.CheckConstraint("tentativas >= 0", name="ck_recebimento_tentativas"),
        sa.ForeignKeyConstraint(
            ["canal_id"],
            ["webhook.canal_drive.canal_id"],
            name="fk_recebimento_canal_id_canal_drive",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("message_id", name="pk_recebimento"),
        sa.UniqueConstraint("provedor", "chave_externa", name="uq_recebimento_chave_externa"),
        schema="webhook",
    )
    op.create_index(
        "ix_recebimento_pendente",
        "recebimento",
        ["recebido_em"],
        schema="webhook",
        postgresql_where=sa.text("publicado_em IS NULL"),
    )

    op.create_table(
        "sincronizacao_fonte",
        sa.Column("fonte_id", sa.Text(), nullable=False),
        sa.Column("cursor", sa.Text(), nullable=True),
        sa.Column("estado", sa.Text(), nullable=False),
        sa.Column("concluida_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "estado IN ('ociosa', 'em_andamento', 'falha')",
            name="ck_sincronizacao_fonte_estado",
        ),
        sa.PrimaryKeyConstraint("fonte_id", name="pk_sincronizacao_fonte"),
        schema="webhook",
    )


def downgrade() -> None:
    op.drop_table("sincronizacao_fonte", schema="webhook")
    op.drop_index("ix_recebimento_pendente", table_name="recebimento", schema="webhook")
    op.drop_table("recebimento", schema="webhook")
    op.drop_index("ix_canal_drive_fonte_estado", table_name="canal_drive", schema="webhook")
    op.drop_table("canal_drive", schema="webhook")
    op.execute("DROP SCHEMA IF EXISTS webhook")
