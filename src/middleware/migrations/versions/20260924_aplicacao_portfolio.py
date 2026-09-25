"""Controle de versão e auditoria da aplicação dos eventos do portfólio.

Seção 9.1.2.7.2 do Projeto.md, "Consumo, ordenação e persistência".
`webhook.versao_entidade` guarda a última versão aplicada por
`(source_id, event_type, entity_id)`, e `webhook.auditoria_portfolio`, o
desfecho de cada evento com os campos anteriores e novos autorizados. Ver
app/webhooks/tabelas.py e app/webhooks/portfolio/aplicacao.py.

Revision ID: 20260924_aplicacao_portfolio
Revises: 20260924_webhook_portfolio
Create Date: 2026-09-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260924_aplicacao_portfolio"
down_revision: str | None = "20260924_webhook_portfolio"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TIPOS = "'projeto.status_alterado', 'marco.alterado', 'risco.alterado'"
_RESULTADOS = "'aplicado', 'sem_diferenca', 'repetido', 'ignorado_antigo'"


def upgrade() -> None:
    op.create_table(
        "versao_entidade",
        sa.Column("source_id", sa.Text(), nullable=False),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("entity_id", sa.Text(), nullable=False),
        sa.Column("versao", sa.BigInteger(), nullable=False),
        sa.Column("dados_sha256", sa.LargeBinary(), nullable=False),
        sa.Column("atualizada_em", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(f"event_type IN ({_TIPOS})", name="ck_versao_entidade_event_type"),
        sa.CheckConstraint("versao >= 0", name="ck_versao_entidade_versao"),
        sa.PrimaryKeyConstraint("source_id", "event_type", "entity_id", name="pk_versao_entidade"),
        schema="webhook",
    )
    op.create_table(
        "auditoria_portfolio",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("message_id", sa.Text(), nullable=False),
        sa.Column("source_id", sa.Text(), nullable=False),
        sa.Column("event_id", sa.Text(), nullable=False),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("projeto_codigo", sa.Text(), nullable=False),
        sa.Column("entity_id", sa.Text(), nullable=False),
        sa.Column("versao", sa.BigInteger(), nullable=False),
        sa.Column("anteriores", postgresql.JSONB(), nullable=False),
        sa.Column("novos", postgresql.JSONB(), nullable=False),
        sa.Column("resultado", sa.Text(), nullable=False),
        sa.Column("registrado_em", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            f"resultado IN ({_RESULTADOS})", name="ck_auditoria_portfolio_resultado"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_auditoria_portfolio"),
        schema="webhook",
    )
    op.create_index(
        "ix_auditoria_portfolio_entidade",
        "auditoria_portfolio",
        ["projeto_codigo", "entity_id"],
        schema="webhook",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_auditoria_portfolio_entidade", table_name="auditoria_portfolio", schema="webhook"
    )
    op.drop_table("auditoria_portfolio", schema="webhook")
    op.drop_table("versao_entidade", schema="webhook")
