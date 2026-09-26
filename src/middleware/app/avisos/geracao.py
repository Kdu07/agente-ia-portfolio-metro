"""Geração dos avisos a partir de um evento do portfólio aplicado.

Roda no consumidor, na mesma transação da aplicação (seção 9.1.2.7.2):
alteração, auditoria, avisos e `processado_em` se confirmam juntos, e a
reentrega não duplica aviso (`(source_id, event_id, usuario_id)` único).

Regras do contrato:

- só `aplicado` avisa: versão antiga, repetida ou sem diferença material
  não notifica ninguém;
- candidatas são as adesões **ativas** ao tipo de evento no projeto; o
  payload externo nunca escolhe destinatário;
- só recebe quem **ainda** tem acesso ao projeto, pela mesma regra da
  sessão (vínculo em `usuario_projeto` ou diretoria);
- risco com severidade mínima avisa quando o estado anterior **ou** o novo
  alcança o mínimo (`probabilidade × impacto`), inclusive numa redução.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.avisos.modelos import PreferenciaAviso
from app.avisos.repositorio import AvisoRepository, PreferenciaRepository, usuarios_com_acesso
from app.webhooks.modelos import ResultadoAplicacao, TipoEventoPortfolio

if TYPE_CHECKING:
    from app.webhooks.portfolio.aplicacao import Aplicacao


def severidade(campos: dict[str, Any]) -> int | None:
    """`probabilidade × impacto`, ou nada se o estado não tem os dois."""
    probabilidade, impacto = campos.get("probabilidade"), campos.get("impacto")
    if isinstance(probabilidade, int) and isinstance(impacto, int):
        return probabilidade * impacto
    return None


def deve_avisar(preferencia: PreferenciaAviso, aplicacao: Aplicacao) -> bool:
    if aplicacao.resultado is not ResultadoAplicacao.APLICADO:
        return False
    minimo = preferencia.severidade_minima
    if aplicacao.event_type is not TipoEventoPortfolio.RISCO or minimo is None:
        return True
    extremos = [severidade(aplicacao.anteriores), severidade(aplicacao.novos)]
    return any(valor is not None and valor >= minimo for valor in extremos)


def diferencas(anteriores: dict[str, Any], novos: dict[str, Any]) -> dict[str, Any]:
    """Só os campos que mudaram, com o valor de antes e o de agora."""
    return {
        campo: {"de": anteriores.get(campo), "para": valor}
        for campo, valor in novos.items()
        if anteriores.get(campo) != valor
    }


async def gerar_avisos(sessao: AsyncSession, aplicacao: Aplicacao, *, agora: datetime) -> int:
    """Cria os avisos elegíveis; devolve quantos foram criados."""
    if aplicacao.resultado is not ResultadoAplicacao.APLICADO:
        return 0
    candidatas = await PreferenciaRepository(sessao).candidatas(
        aplicacao.projeto_codigo, aplicacao.event_type
    )
    if not candidatas:
        return 0
    com_acesso = await usuarios_com_acesso(sessao, aplicacao.projeto_codigo)
    avisos = AvisoRepository(sessao)
    mudancas = diferencas(aplicacao.anteriores, aplicacao.novos)
    criados = 0
    for preferencia in candidatas:
        if preferencia.usuario_id not in com_acesso or not deve_avisar(preferencia, aplicacao):
            continue
        if await avisos.criar(
            usuario_id=preferencia.usuario_id,
            projeto_codigo=aplicacao.projeto_codigo,
            source_id=aplicacao.source_id,
            event_id=aplicacao.event_id,
            event_type=aplicacao.event_type,
            entity_id=aplicacao.entity_id,
            versao=aplicacao.versao,
            diferencas=mudancas,
            agora=agora,
        ):
            criados += 1
    return criados
