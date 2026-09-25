"""Payload v1 do WH-02: leitura, schema estrito e escopo da fonte.

Cada caso é uma regra da seção 9.1.2.7.2 do Projeto.md: chave JSON
repetida, campo desconhecido, tipo coercível mas incorreto, data inválida,
enum fora do modelo de persistência e fonte do corpo diferente da que
assinou. O vínculo com o banco está em
tests/integration/test_webhook_portfolio.py.
"""

import copy
import json

import pytest

from app.auth.webhooks import WebhookRecusado
from app.webhooks.modelos import FontePortfolio, TipoEventoPortfolio
from app.webhooks.portfolio.evento import (
    EventoMarco,
    EventoProjeto,
    EventoRisco,
    autorizar,
    ler_json,
    validar_evento,
)

FONTE = "portfolio_sintetico"
BASE = {
    "schema_version": 1,
    "event_id": "d14a8d53-4f74-4aac-a37b-521273a082ec",
    "source_id": FONTE,
    "event_type": "risco.alterado",
    "occurred_at": "2026-09-22T12:00:00Z",
    "projeto_codigo": "PRJ-2024-018",
    "entity_id": "RSK-7",
    "version": 8,
    "data": {"status": "monitorado", "probabilidade": 4, "impacto": 5},
}
MARCO = {"status": "atrasado", "data_prevista": "2026-10-01", "data_real": None}


def evento(**mudancas):
    corpo = copy.deepcopy(BASE)
    corpo.update(mudancas)
    return corpo


def validar(corpo, fonte=FONTE):
    return validar_evento(ler_json(json.dumps(corpo).encode()), fonte_autenticada=fonte)


def status_da_recusa(corpo, fonte=FONTE) -> int:
    with pytest.raises(WebhookRecusado) as recusa:
        validar(corpo, fonte)
    return recusa.value.status


def test_risco_valido():
    assert isinstance(validar(evento()), EventoRisco)


def test_marco_valido_com_data_real_nula():
    assert isinstance(validar(evento(event_type="marco.alterado", data=MARCO)), EventoMarco)


def test_projeto_valido_tem_a_entidade_igual_ao_projeto():
    corpo = evento(
        event_type="projeto.status_alterado", entity_id="PRJ-2024-018", data={"status": "suspenso"}
    )
    assert isinstance(validar(corpo), EventoProjeto)


@pytest.mark.parametrize(
    "corpo",
    [
        pytest.param(evento(schema_version=True), id="schema_version true"),
        pytest.param(evento(schema_version=1.0), id="schema_version 1.0"),
        pytest.param(evento(schema_version=2), id="schema_version 2"),
        pytest.param(evento(version="8"), id="version em texto"),
        pytest.param(evento(version=True), id="version booleana"),
        pytest.param(evento(version=0), id="version zero"),
        pytest.param(evento(version=2**53), id="version acima de 2^53-1"),
        pytest.param(
            evento(data={"status": "monitorado", "probabilidade": 4.0, "impacto": 5}),
            id="probabilidade 4.0",
        ),
        pytest.param(
            evento(data={"status": "monitorado", "probabilidade": 6, "impacto": 5}),
            id="probabilidade 6",
        ),
        pytest.param(
            evento(data={"status": "resolvido", "probabilidade": 4, "impacto": 5}),
            id="status fora do enum",
        ),
        pytest.param(evento(extra=1), id="campo desconhecido no topo"),
        pytest.param(
            evento(data={"status": "monitorado", "probabilidade": 4, "impacto": 5, "x": 1}),
            id="campo desconhecido em data",
        ),
        pytest.param({k: v for k, v in BASE.items() if k != "version"}, id="campo faltando"),
        pytest.param(evento(event_id="d14a8d53-4f74-1aac-a37b-521273a082ec"), id="UUID v1"),
        pytest.param(evento(event_id=BASE["event_id"].upper()), id="UUID maiúsculo"),
        pytest.param(evento(occurred_at="2026-09-22T12:00:00"), id="instante sem Z"),
        pytest.param(evento(occurred_at="2026-09-22T12:00:00.000Z"), id="instante com ms"),
        pytest.param(evento(occurred_at="2026-09-22T25:00:00Z"), id="hora 25"),
        pytest.param(evento(event_type="risco.apagado"), id="tipo desconhecido"),
        pytest.param(evento(entity_id="a\nb"), id="caractere de controle"),
        pytest.param(evento(entity_id="x" * 129), id="identificador longo"),
        pytest.param(
            evento(event_type="marco.alterado", data=dict(MARCO, data_prevista="2026-02-30")),
            id="data 30/02",
        ),
        pytest.param(
            evento(
                event_type="marco.alterado",
                data={k: v for k, v in MARCO.items() if k != "data_real"},
            ),
            id="data_real ausente",
        ),
        pytest.param(
            evento(event_type="projeto.status_alterado", data={"status": "suspenso"}),
            id="projeto com entidade diferente",
        ),
    ],
)
def test_schema_invalido_responde_422(corpo):
    assert status_da_recusa(corpo) == 422


def test_corpo_que_nao_e_objeto_responde_422():
    with pytest.raises(WebhookRecusado) as recusa:
        validar_evento(ler_json(b"[1, 2]"), fonte_autenticada=FONTE)

    assert recusa.value.status == 422


def test_fonte_do_corpo_diferente_da_assinatura_responde_401():
    assert status_da_recusa(evento(), fonte="outra_fonte") == 401


@pytest.mark.parametrize(
    "corpo",
    [
        b'{"version": 1, "version": 2}',
        b'{"schema_version":',
        b'{"texto": "\xff"}',
    ],
    ids=["chave repetida", "JSON truncado", "UTF-8 inválido"],
)
def test_json_ilegivel_responde_400(corpo):
    with pytest.raises(WebhookRecusado) as recusa:
        ler_json(corpo)

    assert recusa.value.status == 400


FONTE_CADASTRADA = FontePortfolio(
    source_id=FONTE,
    planilha_id="planilha",
    projetos=frozenset({"PRJ-2024-018"}),
    tipos=frozenset({TipoEventoPortfolio.RISCO, TipoEventoPortfolio.MARCO}),
    ativa=True,
)


def test_fonte_autorizada_passa():
    autorizar(validar(evento()), FONTE_CADASTRADA)


@pytest.mark.parametrize(
    "corpo,fonte",
    [
        pytest.param(evento(), None, id="fonte sem cadastro"),
        pytest.param(
            evento(),
            FontePortfolio(FONTE, "p", FONTE_CADASTRADA.projetos, FONTE_CADASTRADA.tipos, False),
            id="fonte inativa",
        ),
        pytest.param(evento(projeto_codigo="PRJ-OUTRO"), FONTE_CADASTRADA, id="projeto fora"),
        pytest.param(
            evento(
                event_type="projeto.status_alterado",
                entity_id="PRJ-2024-018",
                data={"status": "suspenso"},
            ),
            FONTE_CADASTRADA,
            id="tipo fora",
        ),
    ],
)
def test_fora_do_escopo_responde_403(corpo, fonte):
    with pytest.raises(WebhookRecusado) as recusa:
        autorizar(validar(corpo), fonte)

    assert (recusa.value.status, recusa.value.codigo) == (403, "WEBHOOK_FORA_DO_ESCOPO")
