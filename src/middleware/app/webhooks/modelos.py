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


class TipoEventoPortfolio(Enum):
    """Eventos que o emissor do WH-02 pode enviar (seção 9.1.2.7.2)."""

    PROJETO_STATUS = "projeto.status_alterado"
    MARCO = "marco.alterado"
    RISCO = "risco.alterado"


class ResultadoAplicacao(Enum):
    """Desfecho da aplicação de um evento do portfólio (seção 9.1.2.7.2)."""

    APLICADO = "aplicado"  # versão maior com diferença material
    SEM_DIFERENCA = "sem_diferenca"  # versão maior, mesmos valores: avança sem aviso
    REPETIDO = "repetido"  # mesma versão e mesmos campos: sem efeito
    IGNORADO_ANTIGO = "ignorado_antigo"  # versão menor que a já aplicada


class EstadoSincronizacao(Enum):
    """Estado operacional da reconciliação de uma fonte documental."""

    OCIOSA = "ociosa"
    EM_ANDAMENTO = "em_andamento"
    FALHA = "falha"


@dataclass(frozen=True)
class CanalRegistrado:
    """Canal do Drive como a operação o enxerga: sem o hash do token."""

    canal_id: str
    fonte_id: str
    estado: EstadoCanal
    recurso_id: str | None
    expira_em: datetime
    ativado_em: datetime | None


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
    # Hash dos bytes exatos do corpo, só no WH-02: distingue a repetição
    # idêntica (204) de outro corpo com o mesmo `event_id` (409).
    corpo_sha256: bytes | None = None


@dataclass(frozen=True)
class FontePortfolio:
    """Cadastro de um emissor do WH-02 e do que ele pode alterar.

    Autenticar a assinatura prova quem enviou; este cadastro decide o que
    esse emissor está autorizado a alterar. Fora dele, a resposta é 403.
    """

    source_id: str
    planilha_id: str
    projetos: frozenset[str]
    tipos: frozenset[TipoEventoPortfolio]
    ativa: bool

    def autoriza(self, projeto_codigo: str, tipo: TipoEventoPortfolio) -> bool:
        return self.ativa and projeto_codigo in self.projetos and tipo in self.tipos
