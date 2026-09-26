"""Registra o tempo de cada etapa do pipeline na interação.

A latência total (`latencia_ms`) diz quanto a mensagem custou, mas não
onde. A coluna nova guarda o tempo por etapa percorrida, que é o que o
painel de intenções precisa para apontar qual barreira pesa no pedágio
descrito na seção 1.3 da Arquitetura.

Anulável porque as interações já gravadas não têm essa medida, e
inventá-la a partir do total atribuiria a uma etapa um tempo que ninguém
mediu.

Revision ID: 20260922_latencia_por_etapa
Revises: 20260921_execucao_em_andamento
Create Date: 2026-09-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260922_latencia_por_etapa"
down_revision: str | None = "20260921_execucao_em_andamento"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "interacao",
        sa.Column("latencia_etapas", postgresql.JSONB(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("interacao", "latencia_etapas")
