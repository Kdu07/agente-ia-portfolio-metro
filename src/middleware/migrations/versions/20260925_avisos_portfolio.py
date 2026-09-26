"""Preferências e avisos dos eventos do portfólio.

Seção 9.1.2.7.2 do Projeto.md, "Preferências de aviso e autorização".
`preferencia_aviso` guarda a adesão única por usuário, projeto e tipo de
evento, desativada por padrão, com severidade mínima só para riscos;
`aviso` guarda os avisos privados, sem duplicidade por evento e usuário.
Ver app/avisos/tabelas.py.

Revision ID: 20260925_avisos_portfolio
Revises: 20260924_aplicacao_portfolio
Create Date: 2026-09-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260925_avisos_portfolio"
down_revision: str | None = "20260924_aplicacao_portfolio"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TIPOS = "event_type IN ('projeto.status_alterado', 'marco.alterado', 'risco.alterado')"


def upgrade() -> None:
    op.create_table(
        "preferencia_aviso",
        sa.Column("usuario_id", sa.Text(), nullable=False),
        sa.Column("projeto_codigo", sa.Text(), nullable=False),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("ativa", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("severidade_minima", sa.Integer(), nullable=True),
        sa.Column("atualizada_em", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(_TIPOS, name="ck_preferencia_aviso_event_type"),
        sa.CheckConstraint(
            "severidade_minima IS NULL OR (event_type = 'risco.alterado' "
            "AND severidade_minima BETWEEN 1 AND 25)",
            name="ck_preferencia_aviso_severidade_minima",
        ),
        sa.ForeignKeyConstraint(
            ["usuario_id"],
            ["usuario.id"],
            name="fk_preferencia_aviso_usuario_id_usuario",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "usuario_id", "projeto_codigo", "event_type", name="pk_preferencia_aviso"
        ),
    )
    op.create_index(
        "ix_preferencia_aviso_candidatas",
        "preferencia_aviso",
        ["projeto_codigo", "event_type"],
    )
    op.create_table(
        "aviso",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("usuario_id", sa.Text(), nullable=False),
        sa.Column("projeto_codigo", sa.Text(), nullable=False),
        sa.Column("source_id", sa.Text(), nullable=False),
        sa.Column("event_id", sa.Text(), nullable=False),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("entity_id", sa.Text(), nullable=False),
        sa.Column("versao", sa.BigInteger(), nullable=False),
        sa.Column("diferencas", postgresql.JSONB(), nullable=False),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("lido_em", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(_TIPOS, name="ck_aviso_event_type"),
        sa.ForeignKeyConstraint(
            ["usuario_id"], ["usuario.id"], name="fk_aviso_usuario_id_usuario", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_aviso"),
        sa.UniqueConstraint("source_id", "event_id", "usuario_id", name="uq_aviso_evento_usuario"),
    )
    op.create_index("ix_aviso_usuario_criado", "aviso", ["usuario_id", sa.text("criado_em DESC")])


def downgrade() -> None:
    op.drop_index("ix_aviso_usuario_criado", table_name="aviso")
    op.drop_table("aviso")
    op.drop_index("ix_preferencia_aviso_candidatas", table_name="preferencia_aviso")
    op.drop_table("preferencia_aviso")
