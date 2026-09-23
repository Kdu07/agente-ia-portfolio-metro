"""Consultas de rastreabilidade e retenção do registro de interações."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.persistence.tabelas import InteracaoTabela
from app.pipeline.desfechos import Desfecho


@dataclass(frozen=True)
class ResultadoRastreabilidade:
    """Cobertura dos elementos exigidos nas alterações efetivadas."""

    efetivadas: int
    completas: int

    @property
    def cobertura_percentual(self) -> float:
        if self.efetivadas == 0:
            return 100.0
        return self.completas / self.efetivadas * 100


def _tem_origem(linha: InteracaoTabela) -> bool:
    """Canal identifica a origem; rotinas também precisam do vínculo de disparo."""
    return bool(linha.canal) and (linha.canal != "rotina" or linha.rotina_id is not None)


def _esta_completa(linha: InteracaoTabela) -> bool:
    """Confere autoria, origem e momento sem buscar valores fora do registro."""
    return bool(linha.usuario_id and _tem_origem(linha) and linha.criada_em)


async def medir_rastreabilidade(
    sessao: AsyncSession,
    *,
    usuario_ids: frozenset[str] | None = None,
) -> ResultadoRastreabilidade:
    """Calcula a cobertura sobre alterações efetivamente concluídas.

    No modelo atual, ``encaminhada`` é o único desfecho que representa uma
    alteração efetivada. Bloqueios, recusas, cancelamentos e falhas ficam no
    registro de interações, mas não entram no denominador.
    """
    consulta = select(InteracaoTabela).where(
        InteracaoTabela.desfecho == Desfecho.ENCAMINHADA.value
    )
    if usuario_ids is not None:
        consulta = consulta.where(InteracaoTabela.usuario_id.in_(usuario_ids))
    resultado = await sessao.execute(consulta)
    linhas = list(resultado.scalars())
    completas = sum(_esta_completa(linha) for linha in linhas)
    return ResultadoRastreabilidade(efetivadas=len(linhas), completas=completas)


async def expurgar_interacoes(
    sessao: AsyncSession,
    *,
    agora: datetime | None = None,
    dias_retencao: int,
    usuario_ids: frozenset[str] | None = None,
) -> int:
    """Remove interações elegíveis e retorna a quantidade removida.

    O corte é estritamente anterior ao prazo: o registro exatamente na borda
    ainda pertence ao período de retenção. O commit continua sendo do
    chamador, como nos demais repositórios.
    """
    if dias_retencao < 1:
        raise ValueError("dias_retencao deve ser positivo")
    instante = agora or datetime.now(UTC)
    corte = instante - timedelta(days=dias_retencao)
    comando = delete(InteracaoTabela).where(InteracaoTabela.criada_em < corte)
    if usuario_ids is not None:
        comando = comando.where(InteracaoTabela.usuario_id.in_(usuario_ids))
    resultado = await sessao.execute(comando)
    return int(resultado.rowcount or 0)
