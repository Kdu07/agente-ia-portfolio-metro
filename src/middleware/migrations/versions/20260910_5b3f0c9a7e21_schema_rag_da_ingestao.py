"""schema rag da ingestão

Revision ID: 5b3f0c9a7e21
Revises: e70ba6c34d95
Create Date: 2026-09-10 10:00:00.000000-03:00

Cria o schema `rag` com o registro da ingestão (`rag.arquivo`) e o texto
dos trechos indexados (`rag.trecho`). Ver app/rag/tabelas.py.

Revisada contra o metadata: o autogenerate não cria schema — o `CREATE
SCHEMA` abaixo é o que ele não faria — e não inventa índice parcial nem
`CHECK`; os dois estão declarados no modelo.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "5b3f0c9a7e21"
down_revision: str | None = "e70ba6c34d95"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_PERFIS = "perfis <@ ARRAY['diretoria', 'lider_projeto', 'membro_equipe']::text[]"


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS rag")
    op.create_table(
        "arquivo",
        sa.Column("origem_id", sa.Text(), nullable=False),
        sa.Column("nome", sa.Text(), nullable=False),
        sa.Column("mime", sa.Text(), nullable=False),
        sa.Column("md5", sa.Text(), nullable=True),
        sa.Column("modificado_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("link", sa.Text(), nullable=True),
        sa.Column("documento_id", sa.Text(), nullable=True),
        sa.Column("codigo", sa.Text(), nullable=True),
        sa.Column("tipo", sa.Text(), nullable=True),
        sa.Column("versao", sa.Integer(), nullable=True),
        sa.Column("periodo", sa.Text(), nullable=True),
        sa.Column("data_referencia", sa.Date(), nullable=True),
        sa.Column("projeto", sa.Text(), nullable=True),
        sa.Column("classificacao", sa.Text(), nullable=True),
        sa.Column("perfis", postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column("situacao", sa.Text(), nullable=False),
        sa.Column("motivo", sa.Text(), nullable=True),
        sa.Column(
            "observacoes",
            postgresql.ARRAY(sa.Text()),
            server_default=sa.text("'{}'::text[]"),
            nullable=False,
        ),
        sa.Column(
            "metadados",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("assinatura", sa.Text(), nullable=True),
        sa.Column("total_trechos", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("visto_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("indexado_em", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "situacao IN ('indexado', 'substituido', 'quarentena', 'nao_identificado', "
            "'ignorado', 'removido')",
            name=op.f("ck_arquivo_situacao"),
        ),
        sa.CheckConstraint(_PERFIS, name=op.f("ck_arquivo_perfis")),
        sa.PrimaryKeyConstraint("origem_id", name=op.f("pk_arquivo")),
        schema="rag",
    )
    op.create_index(
        "ix_arquivo_documento_indexado",
        "arquivo",
        ["documento_id"],
        unique=True,
        schema="rag",
        postgresql_where=sa.text("situacao = 'indexado'"),
    )
    op.create_table(
        "trecho",
        sa.Column("trecho_id", sa.Text(), nullable=False),
        sa.Column("documento_id", sa.Text(), nullable=False),
        sa.Column("origem_id", sa.Text(), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("texto", sa.Text(), nullable=False),
        sa.Column("tokens", sa.Integer(), nullable=False),
        sa.Column("localizador", sa.Text(), nullable=False),
        sa.Column("projeto", sa.Text(), nullable=True),
        sa.Column("perfis", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.CheckConstraint(_PERFIS, name=op.f("ck_trecho_perfis")),
        sa.ForeignKeyConstraint(
            ["origem_id"],
            ["rag.arquivo.origem_id"],
            name=op.f("fk_trecho_origem_id_arquivo"),
            onupdate="CASCADE",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("trecho_id", name=op.f("pk_trecho")),
        schema="rag",
    )
    op.create_index("ix_trecho_documento", "trecho", ["documento_id"], unique=False, schema="rag")


def downgrade() -> None:
    op.drop_index("ix_trecho_documento", table_name="trecho", schema="rag")
    op.drop_table("trecho", schema="rag")
    op.drop_index(
        "ix_arquivo_documento_indexado",
        table_name="arquivo",
        schema="rag",
        postgresql_where=sa.text("situacao = 'indexado'"),
    )
    op.drop_table("arquivo", schema="rag")
    op.execute("DROP SCHEMA IF EXISTS rag")
