"""Adiciona estado transitório às execuções de rotina.

Revision ID: 20260921_execucao_em_andamento
Revises: 20260915_usuario_projeto_sessao
Create Date: 2026-09-21
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260921_execucao_em_andamento"
down_revision: str | None = "20260915_usuario_projeto_sessao"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("ck_execucao_rotina_status", "execucao_rotina", type_="check")
    op.create_check_constraint(
        "ck_execucao_rotina_status",
        "execucao_rotina",
        "status IN ('em_execucao', 'sucesso', 'bloqueada', 'falha')",
    )


def downgrade() -> None:
    # Uma execução aberta não cabe no contrato antigo. A migração reversa a
    # fecha como falha antes de restaurar a restrição, preservando a linha.
    op.execute(
        "UPDATE execucao_rotina "
        "SET status = 'falha', concluida_em = COALESCE(concluida_em, iniciada_em), "
        "erro = COALESCE(erro, 'Execução interrompida por downgrade') "
        "WHERE status = 'em_execucao'"
    )
    op.drop_constraint("ck_execucao_rotina_status", "execucao_rotina", type_="check")
    op.create_check_constraint(
        "ck_execucao_rotina_status",
        "execucao_rotina",
        "status IN ('sucesso', 'bloqueada', 'falha')",
    )
