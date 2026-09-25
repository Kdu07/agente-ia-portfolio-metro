"""Contratos das rotas de preferências e avisos do portfólio (#447).

Não há campo de usuário em nenhum pedido: o dono é sempre o usuário da
sessão. O payload do emissor do WH-02 também nunca escolhe destinatário.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, model_validator

from app.webhooks.modelos import TipoEventoPortfolio


class PreferenciaPedido(BaseModel):
    """Liga ou desliga os avisos de um tipo de evento de um projeto."""

    ativa: bool
    # Só para riscos: `probabilidade × impacto` mínimo, de 1 a 25.
    severidade_minima: int | None = Field(default=None, ge=1, le=25)


class PreferenciaResposta(BaseModel):
    projeto_codigo: str
    event_type: TipoEventoPortfolio
    ativa: bool
    severidade_minima: int | None
    atualizada_em: datetime


class AvisoResposta(BaseModel):
    """Um aviso como a lista e o detalhe o exibem."""

    id: str
    projeto_codigo: str
    event_type: TipoEventoPortfolio
    entity_id: str
    versao: int
    diferencas: dict[str, Any]
    criado_em: datetime
    lido_em: datetime | None


class ContagemAvisos(BaseModel):
    nao_lidos: int


class _TipoComSeveridade(BaseModel):
    event_type: TipoEventoPortfolio
    severidade_minima: int | None

    @model_validator(mode="after")
    def _so_risco_tem_severidade(self) -> "_TipoComSeveridade":
        if self.severidade_minima is not None and self.event_type is not TipoEventoPortfolio.RISCO:
            raise ValueError("severidade_minima só se aplica a risco.alterado")
        return self


def validar_severidade(event_type: TipoEventoPortfolio, severidade_minima: int | None) -> None:
    """Levanta `ValueError` para severidade em tipo que não é risco."""
    _TipoComSeveridade(event_type=event_type, severidade_minima=severidade_minima)
