"""Cadastra os emissores do WH-02 e guarda o hash do corpo recebido.

Contrato da seção 9.1.2.7.2 do Projeto.md. `webhook.fonte_portfolio`
vincula cada `source_id` à planilha e aos projetos e tipos de evento que
ele pode alterar: é o que separa uma fonte autenticada (a assinatura da
#388) de uma fonte autorizada, cuja falta responde 403. A coluna
`recebimento.corpo_sha256` diferencia a repetição idêntica de um mesmo
`event_id` (204) de outro corpo com o mesmo identificador (409). Ver
app/webhooks/tabelas.py.

Revision ID: 20260924_webhook_portfolio
Revises: 20260923_webhook_drive
Create Date: 2026-09-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260924_webhook_portfolio"
down_revision: str | None = "20260923_webhook_drive"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "recebimento",
        sa.Column("corpo_sha256", sa.LargeBinary(), nullable=True),
        schema="webhook",
    )
    op.create_check_constraint(
        "ck_recebimento_corpo_sha256",
        "recebimento",
        "corpo_sha256 IS NULL OR octet_length(corpo_sha256) = 32",
        schema="webhook",
    )

    op.create_table(
        "fonte_portfolio",
        sa.Column("source_id", sa.Text(), nullable=False),
        sa.Column("planilha_id", sa.Text(), nullable=False),
        sa.Column("projetos", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("tipos", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("ativa", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("criada_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("atualizada_em", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "source_id ~ '^[A-Za-z0-9_-]{1,64}$'", name="ck_fonte_portfolio_source_id"
        ),
        sa.CheckConstraint(
            "tipos <@ ARRAY['projeto.status_alterado', 'marco.alterado', 'risco.alterado']::text[]",
            name="ck_fonte_portfolio_tipos",
        ),
        sa.PrimaryKeyConstraint("source_id", name="pk_fonte_portfolio"),
        schema="webhook",
    )


def downgrade() -> None:
    op.drop_table("fonte_portfolio", schema="webhook")
    op.drop_constraint("ck_recebimento_corpo_sha256", "recebimento", schema="webhook")
    op.drop_column("recebimento", "corpo_sha256", schema="webhook")
