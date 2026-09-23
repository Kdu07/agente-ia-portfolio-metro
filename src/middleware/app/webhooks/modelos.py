"""Vocabulário e registros de domínio dos webhooks.

Os enums geram os `CHECK` das tabelas (ver `tabelas.py`), como em
persistence/: um valor novo no código sem migração vira erro na
migração, e não uma linha recusada em produção.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any


class Provedor(Enum):
    """Emissor externo do webhook (WH-01 e WH-02 da seção 9.1.2.7)."""

    GOOGLE_DRIVE = "google_drive"
    APPS_SCRIPT = "apps_script"


class EstadoCanal(Enum):
    """Ciclo de vida de uma inscrição `changes.watch` do Drive.

    `pendente` existe entre gravar o canal e confirmar a inscrição: o
    `sync` do Google pode chegar antes da resposta de `changes.watch`.
    """

    PENDENTE = "pendente"
    ATIVO = "ativo"
    ENCERRADO = "encerrado"


class EstadoSincronizacao(Enum):
    """Estado operacional da reconciliação de uma fonte documental."""

    OCIOSA = "ociosa"
    EM_ANDAMENTO = "em_andamento"
    FALHA = "falha"


@dataclass(frozen=True)
class Recebimento:
    """Uma notificação aceita, com os identificadores do evento interno.

    `message_id` e `correlation_id` são atribuídos uma única vez, no
    primeiro registro: uma repetição da mesma notificação reencontra os
    mesmos UUIDs, e o consumidor deduplica por eles.
    """

    message_id: str
    correlation_id: str
    provedor: Provedor
    chave_externa: str
    fonte_id: str
    canal_id: str | None
    evento: dict[str, Any]
    recebido_em: datetime
    publicado_em: datetime | None
    processado_em: datetime | None
    tentativas: int
    erro_codigo: str | None
