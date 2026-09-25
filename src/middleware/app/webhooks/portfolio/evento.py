"""Payload versão 1 do WH-02: leitura, schema, escopo e vínculo da entidade.

Segue a ordem da seção 9.1.2.7.2 do Projeto.md, depois de a assinatura
(#388) ter autenticado a fonte:

1. `ler_json` recusa JSON malformado e **chaves duplicadas** com 400. O
   `json.loads` padrão ficaria com a última ocorrência em silêncio, e o
   emissor assinou um corpo que o receptor leria de outro jeito;
2. `validar_evento` exige que `source_id` seja a fonte autenticada (401) e
   aplica o schema com `strict`: nada de `"5"` virando `5`, `true` virando
   `1` ou campo desconhecido aceito calado. Violação responde 422;
3. `autorizar` decide pelo cadastro da fonte se ela pode alterar aquele
   projeto com aquele tipo de evento (403);
4. `conferir_vinculo` só depois consulta o banco: projeto inexistente ou
   entidade de outro projeto responde 422. Conferir antes de autorizar
   revelaria a quem não tem escopo o que existe no portfólio.

Os enums vêm dos modelos de persistência (`StatusProjeto`, `StatusMarco`,
`StatusRisco`): um nome de coluna ou valor arbitrário nunca vira
instrução de atualização.
"""

import json
import re
from datetime import date, datetime
from typing import Annotated, Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    TypeAdapter,
    ValidationError,
    field_validator,
    model_validator,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.webhooks import WebhookRecusado
from app.persistence.models import StatusMarco, StatusProjeto, StatusRisco
from app.persistence.tabelas_portfolio import MarcoTabela, ProjetoTabela, RiscoTabela
from app.webhooks.modelos import FontePortfolio, TipoEventoPortfolio

MAIOR_VERSAO = 9007199254740991  # 2**53 - 1, o maior inteiro exato do emissor em JavaScript

_UUID_V4 = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}")
_INSTANTE_UTC = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")

Identificador = Annotated[
    str, StringConstraints(min_length=1, max_length=128, pattern=r"^[^\x00-\x1f\x7f]+$")
]
Nota = Annotated[int, Field(ge=1, le=5)]
Data = Annotated[str, StringConstraints(pattern=r"^\d{4}-\d{2}-\d{2}$")]


class _Estrito(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)


def _data_valida(valor: str | None) -> str | None:
    if valor is not None:
        date.fromisoformat(valor)  # 2026-02-30 passa na regex, não no calendário
    return valor


class DadosProjeto(_Estrito):
    status: Literal[tuple(s.value for s in StatusProjeto)]  # type: ignore[valid-type]


class DadosMarco(_Estrito):
    status: Literal[tuple(s.value for s in StatusMarco)]  # type: ignore[valid-type]
    data_prevista: Data
    data_real: Data | None

    _datas = field_validator("data_prevista", "data_real")(_data_valida)


class DadosRisco(_Estrito):
    status: Literal[tuple(s.value for s in StatusRisco)]  # type: ignore[valid-type]
    probabilidade: Nota
    impacto: Nota


class _EventoBase(_Estrito):
    # `Literal[1]` compararia por igualdade e aceitaria `true` e `1.0`;
    # inteiro estrito entre 1 e 1 recusa os dois.
    schema_version: Annotated[int, Field(ge=1, le=1)]
    event_id: str
    source_id: Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9_-]{1,64}$")]
    occurred_at: str
    projeto_codigo: Identificador
    entity_id: Identificador
    version: Annotated[int, Field(ge=1, le=MAIOR_VERSAO)]

    @field_validator("event_id")
    @classmethod
    def _uuid_v4(cls, valor: str) -> str:
        if not _UUID_V4.fullmatch(valor):
            raise ValueError("event_id deve ser UUID v4 em minúsculas")
        return valor

    @field_validator("occurred_at")
    @classmethod
    def _instante(cls, valor: str) -> str:
        if not _INSTANTE_UTC.fullmatch(valor):
            raise ValueError("occurred_at deve seguir YYYY-MM-DDTHH:mm:ssZ")
        datetime.fromisoformat(valor)  # 25:61 passa na regex, não aqui
        return valor


class EventoProjeto(_EventoBase):
    event_type: Literal["projeto.status_alterado"]
    data: DadosProjeto

    @model_validator(mode="after")
    def _entidade_e_o_projeto(self) -> "EventoProjeto":
        # No primeiro tipo, a entidade é o próprio projeto.
        if self.entity_id != self.projeto_codigo:
            raise ValueError("entity_id deve ser o código do projeto")
        return self


class EventoMarco(_EventoBase):
    event_type: Literal["marco.alterado"]
    data: DadosMarco


class EventoRisco(_EventoBase):
    event_type: Literal["risco.alterado"]
    data: DadosRisco


EventoPortfolio = Annotated[
    EventoProjeto | EventoMarco | EventoRisco, Field(discriminator="event_type")
]
_VALIDADOR = TypeAdapter(EventoPortfolio)


def _sem_repeticoes(pares: list[tuple[str, Any]]) -> dict[str, Any]:
    objeto: dict[str, Any] = {}
    for chave, valor in pares:
        if chave in objeto:
            raise ValueError("chave JSON repetida")
        objeto[chave] = valor
    return objeto


def ler_json(corpo: bytes) -> Any:
    """Decodifica o corpo em UTF-8 estrito; malformado ou repetido responde 400."""
    try:
        return json.loads(corpo.decode("utf-8"), object_pairs_hook=_sem_repeticoes)
    except (UnicodeDecodeError, ValueError):
        raise WebhookRecusado(400, "WEBHOOK_INVALIDO") from None


def validar_evento(
    dados: Any, *, fonte_autenticada: str
) -> EventoProjeto | EventoMarco | EventoRisco:
    """Aplica o schema v1; a fonte do corpo precisa ser a que assinou."""
    if isinstance(dados, dict) and dados.get("source_id") != fonte_autenticada:
        # O corpo não pode falar em nome de outra fonte que a da assinatura.
        raise WebhookRecusado(401, "WEBHOOK_NAO_AUTORIZADO")
    try:
        return _VALIDADOR.validate_python(dados, strict=True)
    except (ValidationError, ValueError):
        raise WebhookRecusado(422, "WEBHOOK_PAYLOAD_INVALIDO") from None


def autorizar(
    evento: EventoProjeto | EventoMarco | EventoRisco, fonte: FontePortfolio | None
) -> None:
    """Fonte sem cadastro, inativa ou fora do escopo responde 403."""
    tipo = TipoEventoPortfolio(evento.event_type)
    if fonte is None or not fonte.autoriza(evento.projeto_codigo, tipo):
        raise WebhookRecusado(403, "WEBHOOK_FORA_DO_ESCOPO")


async def conferir_vinculo(
    sessao: AsyncSession, evento: EventoProjeto | EventoMarco | EventoRisco
) -> None:
    """Projeto inexistente ou entidade de outro projeto responde 422."""
    projeto = await sessao.scalar(
        select(ProjetoTabela.codigo).where(ProjetoTabela.codigo == evento.projeto_codigo)
    )
    if projeto is None:
        raise WebhookRecusado(422, "WEBHOOK_PAYLOAD_INVALIDO")
    if isinstance(evento, EventoProjeto):
        return
    tabela = MarcoTabela if isinstance(evento, EventoMarco) else RiscoTabela
    dono = await sessao.scalar(select(tabela.projeto_codigo).where(tabela.id == evento.entity_id))
    if dono != evento.projeto_codigo:
        raise WebhookRecusado(422, "WEBHOOK_PAYLOAD_INVALIDO")
