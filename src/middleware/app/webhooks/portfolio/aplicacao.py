"""Aplicação dos eventos do portfólio no banco (Projeto.md 9.1.2.7.2).

Roda no consumidor (#394), na transação em que o recebimento é marcado
como processado. Segue "Consumo, ordenação e persistência":

1. a fonte, o escopo e o pertencimento da entidade são **revalidados**:
   receber `202` não garante que a fonte continue autorizada quando o
   evento é processado. Revogada, a falha é definitiva, sem alterar dados;
2. o controle de versão de `(source_id, event_type, entity_id)` é travado
   (`SELECT ... FOR UPDATE`). Versão menor termina como `ignorado_antigo`;
   mesma versão com os mesmos campos, `repetido`; mesma versão com campos
   diferentes é conflito permanente — quarentena em `prata.failed`, nunca
   sobrescrita silenciosa; versão maior aplica o snapshot completo, mesmo
   com lacuna, porque perder um estado intermediário não impede convergir;
3. só os campos que o contrato autoriza para o tipo são escritos, e a
   auditoria guarda os valores anteriores e novos desses campos. Versão
   maior sem diferença material avança a versão como `sem_diferenca`, que
   não gera aviso;
4. na mesma transação, os avisos das adesões elegíveis (#447,
   `app/avisos/geracao.py`).
"""

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.webhooks import WebhookRecusado
from app.avisos.geracao import gerar_avisos
from app.mensageria.consumidor import FalhaDefinitiva
from app.persistence.tabelas_portfolio import MarcoTabela, ProjetoTabela, RiscoTabela
from app.schemas.mensagem import MensagemEvento
from app.webhooks.modelos import ResultadoAplicacao, TipoEventoPortfolio
from app.webhooks.portfolio.evento import (
    EventoMarco,
    EventoProjeto,
    EventoRisco,
    autorizar,
    conferir_vinculo,
    validar_evento,
)
from app.webhooks.repositorio import FontePortfolioRepository
from app.webhooks.tabelas import AuditoriaPortfolioTabela, VersaoEntidadeTabela

Evento = EventoProjeto | EventoMarco | EventoRisco

# Campos que cada tipo pode escrever, e em qual tabela. Nada além disso.
_DESTINOS = {
    TipoEventoPortfolio.PROJETO_STATUS: (ProjetoTabela, ProjetoTabela.codigo, ("status",)),
    TipoEventoPortfolio.MARCO: (
        MarcoTabela,
        MarcoTabela.id,
        ("status", "data_prevista", "data_real"),
    ),
    TipoEventoPortfolio.RISCO: (
        RiscoTabela,
        RiscoTabela.id,
        ("status", "probabilidade", "impacto"),
    ),
}
_CAMPOS_DE_DATA = frozenset({"data_prevista", "data_real"})
_HASH_INICIAL = bytes(32)  # versão 0: nenhum evento aplicado ainda


@dataclass(frozen=True)
class Aplicacao:
    """O que aconteceu com um evento, para a auditoria e para os avisos."""

    resultado: ResultadoAplicacao
    source_id: str
    event_id: str
    event_type: TipoEventoPortfolio
    projeto_codigo: str
    entity_id: str
    versao: int
    anteriores: dict[str, Any]
    novos: dict[str, Any]


def _serializar(valor: Any) -> Any:
    return valor.isoformat() if isinstance(valor, date) else valor


def _hash(dados: dict[str, Any]) -> bytes:
    return hashlib.sha256(json.dumps(dados, sort_keys=True).encode("utf-8")).digest()


async def aplicar_evento(
    sessao: AsyncSession, evento: Evento, *, message_id: str, agora: datetime
) -> Aplicacao:
    """Aplica o evento validado; levanta `FalhaDefinitiva` para conflito ou escopo."""
    tipo = TipoEventoPortfolio(evento.event_type)
    try:
        autorizar(evento, await FontePortfolioRepository(sessao).obter(evento.source_id))
        await conferir_vinculo(sessao, evento)
    except WebhookRecusado:
        raise FalhaDefinitiva("ESCOPO_REVOGADO") from None

    novos = evento.data.model_dump()
    hash_novos = _hash(novos)
    chave = {
        "source_id": evento.source_id,
        "event_type": tipo.value,
        "entity_id": evento.entity_id,
    }
    await sessao.execute(
        pg_insert(VersaoEntidadeTabela)
        .values(**chave, versao=0, dados_sha256=_HASH_INICIAL, atualizada_em=agora)
        .on_conflict_do_nothing()
    )
    controle = await sessao.scalar(
        select(VersaoEntidadeTabela).filter_by(**chave).with_for_update()
    )

    anteriores: dict[str, Any] = {}
    if evento.version < controle.versao:
        resultado = ResultadoAplicacao.IGNORADO_ANTIGO
    elif evento.version == controle.versao:
        if bytes(controle.dados_sha256) != hash_novos:
            raise FalhaDefinitiva("CONFLITO_DE_VERSAO")
        resultado = ResultadoAplicacao.REPETIDO
    else:
        tabela, identificador, campos = _DESTINOS[tipo]
        entidade = await sessao.scalar(
            select(tabela).where(identificador == evento.entity_id).with_for_update()
        )
        anteriores = {campo: _serializar(getattr(entidade, campo)) for campo in campos}
        if anteriores == novos:
            resultado = ResultadoAplicacao.SEM_DIFERENCA
        else:
            for campo in campos:
                valor = novos[campo]
                if campo in _CAMPOS_DE_DATA and valor is not None:
                    valor = date.fromisoformat(valor)
                setattr(entidade, campo, valor)
            entidade.atualizado_em = agora
            resultado = ResultadoAplicacao.APLICADO
        controle.versao = evento.version
        controle.dados_sha256 = hash_novos
        controle.atualizada_em = agora

    aplicacao = Aplicacao(
        resultado=resultado,
        source_id=evento.source_id,
        event_id=evento.event_id,
        event_type=tipo,
        projeto_codigo=evento.projeto_codigo,
        entity_id=evento.entity_id,
        versao=evento.version,
        anteriores=anteriores,
        novos=novos,
    )
    sessao.add(
        AuditoriaPortfolioTabela(
            id=str(uuid4()),
            message_id=message_id,
            source_id=aplicacao.source_id,
            event_id=aplicacao.event_id,
            event_type=tipo.value,
            projeto_codigo=aplicacao.projeto_codigo,
            entity_id=aplicacao.entity_id,
            versao=aplicacao.versao,
            anteriores=anteriores,
            novos=novos,
            resultado=resultado.value,
            registrado_em=agora,
        )
    )
    return aplicacao


async def tratar_evento_portfolio(evento: MensagemEvento, sessao: AsyncSession) -> None:
    """Tratador do provedor `apps_script` para o consumidor de webhooks."""
    bruto = evento.payload.get("event")
    if not isinstance(bruto, dict):
        raise FalhaDefinitiva("PAYLOAD_INVALIDO")
    try:
        validado = validar_evento(bruto, fonte_autenticada=str(bruto.get("source_id")))
    except WebhookRecusado:
        raise FalhaDefinitiva("PAYLOAD_INVALIDO") from None
    agora = datetime.now(UTC)
    aplicacao = await aplicar_evento(
        sessao, validado, message_id=str(evento.message_id), agora=agora
    )
    await gerar_avisos(sessao, aplicacao, agora=agora)
