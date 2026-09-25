"""schema portfolio para dados estruturados de projetos

Revision ID: 20260915_portfolio
Revises: 5b1f0c9a7d21
Create Date: 2026-09-15 10:00:00.000000-03:00

Cria o schema `portfolio` com tabelas para suportar as intenções de
transação (atualizar avanço, comparar projetos, gerar prévia de relatório).
As tabelas seguem o modelo de dados descrito na seção 4.3 do Projeto.md.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260915_portfolio"
down_revision: str | None = "5b1f0c9a7d21"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_STATUS_PROJETO = (
    "status IN ('planejado', 'em_andamento', 'suspenso', 'concluido', 'cancelado')"
)
_PRIORIDADE = "prioridade IN ('baixa', 'media', 'alta', 'critica')"
_STATUS_RISCO = "status IN ('identificado', 'monitorado', 'mitigado', 'materializado')"
_STATUS_MARCO = "status IN ('nao_iniciado', 'em_andamento', 'concluido', 'atrasado', 'cancelado')"


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS portfolio")

    # Tabela de projetos
    op.create_table(
        "projeto",
        sa.Column("codigo", sa.Text(), nullable=False),
        sa.Column("nome", sa.Text(), nullable=False),
        sa.Column("descricao", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("prioridade", sa.Text(), nullable=False),
        sa.Column("data_inicio", sa.Date(), nullable=True),
        sa.Column("data_fim_prevista", sa.Date(), nullable=True),
        sa.Column("data_fim_real", sa.Date(), nullable=True),
        sa.Column("orcamento_aprovado", sa.Numeric(15, 2), nullable=True),
        sa.Column("orcamento_atual", sa.Numeric(15, 2), nullable=True),
        sa.Column("avanco_percentual", sa.Integer(), nullable=False),
        sa.Column("lider_id", sa.Text(), nullable=True),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(_STATUS_PROJETO, name=op.f("ck_projeto_status")),
        sa.CheckConstraint(_PRIORIDADE, name=op.f("ck_projeto_prioridade")),
        sa.CheckConstraint("avanco_percentual >= 0 AND avanco_percentual <= 100", name=op.f("ck_projeto_avanco")),
        sa.PrimaryKeyConstraint("codigo", name=op.f("pk_projeto")),
        schema="portfolio",
    )
    op.create_index(
        "ix_projeto_status",
        "projeto",
        ["status"],
        unique=False,
        schema="portfolio",
    )
    op.create_index(
        "ix_projeto_lider",
        "projeto",
        ["lider_id"],
        unique=False,
        schema="portfolio",
    )

    # Tabela de riscos
    op.create_table(
        "risco",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("projeto_codigo", sa.Text(), nullable=False),
        sa.Column("descricao", sa.Text(), nullable=False),
        sa.Column("categoria", sa.Text(), nullable=True),
        sa.Column("probabilidade", sa.Integer(), nullable=False),
        sa.Column("impacto", sa.Integer(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("plano_mitigacao", sa.Text(), nullable=True),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("probabilidade >= 1 AND probabilidade <= 5", name=op.f("ck_risco_probabilidade")),
        sa.CheckConstraint("impacto >= 1 AND impacto <= 5", name=op.f("ck_risco_impacto")),
        sa.CheckConstraint(_STATUS_RISCO, name=op.f("ck_risco_status")),
        sa.ForeignKeyConstraint(
            ["projeto_codigo"],
            ["portfolio.projeto.codigo"],
            name=op.f("fk_risco_projeto_codigo_projeto"),
            onupdate="CASCADE",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_risco")),
        schema="portfolio",
    )
    op.create_index(
        "ix_risco_projeto",
        "risco",
        ["projeto_codigo"],
        unique=False,
        schema="portfolio",
    )
    op.create_index(
        "ix_risco_status",
        "risco",
        ["status"],
        unique=False,
        schema="portfolio",
    )

    # Tabela de marcos
    op.create_table(
        "marco",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("projeto_codigo", sa.Text(), nullable=False),
        sa.Column("nome", sa.Text(), nullable=False),
        sa.Column("descricao", sa.Text(), nullable=True),
        sa.Column("data_prevista", sa.Date(), nullable=False),
        sa.Column("data_real", sa.Date(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(_STATUS_MARCO, name=op.f("ck_marco_status")),
        sa.ForeignKeyConstraint(
            ["projeto_codigo"],
            ["portfolio.projeto.codigo"],
            name=op.f("fk_marco_projeto_codigo_projeto"),
            onupdate="CASCADE",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_marco")),
        schema="portfolio",
    )
    op.create_index(
        "ix_marco_projeto",
        "marco",
        ["projeto_codigo"],
        unique=False,
        schema="portfolio",
    )
    op.create_index(
        "ix_marco_data_prevista",
        "marco",
        ["data_prevista"],
        unique=False,
        schema="portfolio",
    )

    # Tabela de indicadores
    op.create_table(
        "indicador",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("projeto_codigo", sa.Text(), nullable=False),
        sa.Column("nome", sa.Text(), nullable=False),
        sa.Column("descricao", sa.Text(), nullable=True),
        sa.Column("valor_atual", sa.Numeric(15, 2), nullable=True),
        sa.Column("valor_meta", sa.Numeric(15, 2), nullable=True),
        sa.Column("unidade", sa.Text(), nullable=True),
        sa.Column("data_medicao", sa.Date(), nullable=True),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["projeto_codigo"],
            ["portfolio.projeto.codigo"],
            name=op.f("fk_indicador_projeto_codigo_projeto"),
            onupdate="CASCADE",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_indicador")),
        schema="portfolio",
    )
    op.create_index(
        "ix_indicador_projeto",
        "indicador",
        ["projeto_codigo"],
        unique=False,
        schema="portfolio",
    )

    # Tabela de relação usuário-projeto
    op.create_table(
        "usuario_projeto",
        sa.Column("usuario_id", sa.Text(), nullable=False),
        sa.Column("projeto_codigo", sa.Text(), nullable=False),
        sa.Column("papel", sa.Text(), nullable=False),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "papel IN ('lider', 'membro', 'observador')",
            name=op.f("ck_usuario_projeto_papel"),
        ),
        sa.ForeignKeyConstraint(
            ["usuario_id"],
            ["usuario.id"],
            name=op.f("fk_usuario_projeto_usuario_id_usuario"),
            onupdate="CASCADE",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["projeto_codigo"],
            ["portfolio.projeto.codigo"],
            name=op.f("fk_usuario_projeto_projeto_codigo_projeto"),
            onupdate="CASCADE",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("usuario_id", "projeto_codigo", name=op.f("pk_usuario_projeto")),
        schema="portfolio",
    )
    op.create_index(
        "ix_usuario_projeto_usuario",
        "usuario_projeto",
        ["usuario_id"],
        unique=False,
        schema="portfolio",
    )
    op.create_index(
        "ix_usuario_projeto_projeto",
        "usuario_projeto",
        ["projeto_codigo"],
        unique=False,
        schema="portfolio",
    )


def downgrade() -> None:
    op.drop_index("ix_usuario_projeto_projeto", table_name="usuario_projeto", schema="portfolio")
    op.drop_index("ix_usuario_projeto_usuario", table_name="usuario_projeto", schema="portfolio")
    op.drop_table("usuario_projeto", schema="portfolio")

    op.drop_index("ix_indicador_projeto", table_name="indicador", schema="portfolio")
    op.drop_table("indicador", schema="portfolio")

    op.drop_index("ix_marco_data_prevista", table_name="marco", schema="portfolio")
    op.drop_index("ix_marco_projeto", table_name="marco", schema="portfolio")
    op.drop_table("marco", schema="portfolio")

    op.drop_index("ix_risco_status", table_name="risco", schema="portfolio")
    op.drop_index("ix_risco_projeto", table_name="risco", schema="portfolio")
    op.drop_table("risco", schema="portfolio")

    op.drop_index("ix_projeto_lider", table_name="projeto", schema="portfolio")
    op.drop_index("ix_projeto_status", table_name="projeto", schema="portfolio")
    op.drop_table("projeto", schema="portfolio")

    op.execute("DROP SCHEMA IF EXISTS portfolio")
