"""Acrescenta o desfecho de guarda sem veredito por indisponibilidade.

Revision ID: 20261006_desfecho_falha_guarda
Revises: 20260925_audio_persistente
Create Date: 2026-10-06
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20261006_desfecho_falha_guarda"
down_revision: str | None = "20260925_audio_persistente"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Mesma ordem do enum, para o CHECK do banco ler igual ao de `tabelas.py`.
_ANTERIORES = (
    "'encaminhada', 'bloqueada_injecao_regra', 'bloqueada_injecao_modelo', "
    "'bloqueada_abuso', 'recusada_fora_escopo', 'recusada_baixa_confianca', "
    "'bloqueada_saida', 'falha_executor'"
)
_ATUAIS = (
    "'encaminhada', 'bloqueada_injecao_regra', 'bloqueada_injecao_modelo', "
    "'bloqueada_abuso', 'recusada_fora_escopo', 'recusada_baixa_confianca', "
    "'bloqueada_saida', 'falha_guarda', 'falha_executor'"
)


def upgrade() -> None:
    op.drop_constraint("ck_interacao_desfecho", "interacao", type_="check")
    op.create_check_constraint(
        "ck_interacao_desfecho",
        "interacao",
        f"desfecho IN ({_ATUAIS})",
    )


def downgrade() -> None:
    # O contrato antigo gravava a indisponibilidade como bloqueio da guarda
    # que falhou. A guarda de injeção roda antes da classificação e a de
    # saída depois, então a intenção vazia separa as duas.
    op.execute(
        "UPDATE interacao SET desfecho = CASE "
        "WHEN intencao_id IS NULL THEN 'bloqueada_injecao_modelo' "
        "ELSE 'bloqueada_saida' END "
        "WHERE desfecho = 'falha_guarda'"
    )
    op.drop_constraint("ck_interacao_desfecho", "interacao", type_="check")
    op.create_check_constraint(
        "ck_interacao_desfecho",
        "interacao",
        f"desfecho IN ({_ANTERIORES})",
    )
