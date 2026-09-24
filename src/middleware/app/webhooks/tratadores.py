"""Tratadores dos eventos de webhook, por provedor.

O consumidor (`app/mensageria/consumidor.py`) escolhe o tratador pelo
`payload.provider` do evento `webhook.received`. Provedor sem tratador é
falha definitiva: o evento vai para `prata.failed` e pode ser reprocessado
depois que o tratador existir, em vez de se perder.
"""

from app.mensageria.consumidor import Tratador
from app.webhooks.modelos import Provedor
from app.webhooks.portfolio.aplicacao import tratar_evento_portfolio


def montar_tratadores() -> dict[str, Tratador]:
    """Tratadores registrados neste processo, por `provider`."""
    return {Provedor.APPS_SCRIPT.value: tratar_evento_portfolio}
