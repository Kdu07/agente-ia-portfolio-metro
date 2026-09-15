"""sessao de login

Revision ID: 5b1f0c9a7d21
Revises: e70ba6c34d95
Create Date: 2026-09-10 21:30:00.000000-03:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "5b1f0c9a7d21"
down_revision: str | None = "5b3f0c9a7e21"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "sessao_usuario",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("usuario_id", sa.Text(), nullable=False),
        sa.Column("perfil", sa.Text(), nullable=False),
        sa.Column(
            "permissoes",
            sa.ARRAY(sa.Text()),
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
        sa.Column("criada_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expira_em", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "perfil IN ('diretoria', 'lider_projeto', 'membro_equipe')",
            name=op.f("ck_sessao_usuario_perfil"),
        ),
        sa.CheckConstraint(
            "permissoes <@ ARRAY['ver_intencoes', 'gerir_rotinas']::text[]",
            name=op.f("ck_sessao_usuario_permissoes"),
        ),
        sa.ForeignKeyConstraint(
            ["usuario_id"],
            ["usuario.id"],
            name=op.f("fk_sessao_usuario_usuario_id_usuario"),
            onupdate="CASCADE",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sessao_usuario")),
    )
    op.create_index("ix_sessao_usuario_usuario", "sessao_usuario", ["usuario_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_sessao_usuario_usuario", table_name="sessao_usuario")
    op.drop_table("sessao_usuario")
