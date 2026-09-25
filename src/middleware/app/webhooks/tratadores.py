"""Tratadores dos eventos de webhook, por provedor.

O consumidor (`app/mensageria/consumidor.py`) escolhe o tratador pelo
`payload.provider` do evento `webhook.received`. Provedor sem tratador é
falha definitiva: o evento vai para `prata.failed` e pode ser reprocessado
depois que o tratador existir, em vez de se perder.
"""

from app.config import settings
from app.mensageria.consumidor import Tratador
from app.webhooks.drive.sincronizacao import SincronizacaoDrive, reindexar_corpus
from app.webhooks.modelos import Provedor
from app.webhooks.portfolio.aplicacao import tratar_evento_portfolio


def _servico_drive():
    # Adiado: o SDK do Google é do extra `rag`, e a credencial só é lida
    # quando chega o primeiro evento do Drive.
    from app.rag.ingestao.drive import criar_servico_drive

    return criar_servico_drive()


def montar_tratadores() -> dict[str, Tratador]:
    """Tratadores registrados neste processo, por `provider`.

    O do Drive só entra com a conta de serviço configurada; sem ela, um
    evento do Drive vai para `prata.failed` em vez de falhar a cada tentativa.
    """
    tratadores: dict[str, Tratador] = {Provedor.APPS_SCRIPT.value: tratar_evento_portfolio}
    if settings.drive_service_account_json and settings.drive_pasta_id:
        drive = SincronizacaoDrive(_servico_drive, reindexar=reindexar_corpus)
        tratadores[Provedor.GOOGLE_DRIVE.value] = drive.tratar
    return tratadores
