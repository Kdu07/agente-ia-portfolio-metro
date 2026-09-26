"""Domínio das preferências e dos avisos do portfólio.

Regras da seção 9.1.2.7.2 do Projeto.md, "Preferências de aviso e
autorização": a preferência é por usuário, projeto e tipo de evento,
desativada por padrão; só riscos admitem severidade mínima
(`probabilidade × impacto`, de 1 a 25); o aviso é privado, fica só dentro
da aplicação e expira em 30 dias.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from app.webhooks.modelos import TipoEventoPortfolio

RETENCAO_AVISOS = timedelta(days=30)
SEVERIDADE_MAXIMA = 25


@dataclass(frozen=True)
class PreferenciaAviso:
    usuario_id: str
    projeto_codigo: str
    event_type: TipoEventoPortfolio
    ativa: bool
    severidade_minima: int | None
    atualizada_em: datetime


@dataclass(frozen=True)
class Aviso:
    id: str
    usuario_id: str
    projeto_codigo: str
    event_type: TipoEventoPortfolio
    entity_id: str
    versao: int
    # Só os campos que mudaram: {"campo": {"de": ..., "para": ...}}.
    diferencas: dict[str, Any]
    criado_em: datetime
    lido_em: datetime | None
