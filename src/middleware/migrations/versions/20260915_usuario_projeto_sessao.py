"""adiciona projetos à sessão do usuário

Revision ID: 20260915_usuario_projeto_sessao
Revises: 20260915_portfolio
Create Date: 2026-09-15 11:00:00.000000-03:00

Adiciona o campo `projetos` (ARRAY de TEXT) à tabela `sessao_usuario`
para armazenar a lista de projetos aos quais o usuário tem acesso.
Isso permite que o controle de acesso por projeto seja aplicado
imediatamente na sessão, sem consultas adicionais.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260915_usuario_projeto_sessao"
down_revision: str | None = "20260915_portfolio"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "sessao_usuario",
        sa.Column(
            "projetos",
            postgresql.ARRAY(sa.Text()),
            server_default=sa.text("'{}'::text[]"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("sessao_usuario", "projetos")
