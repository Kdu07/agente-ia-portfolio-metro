"""Recortes do dashboard, montados a partir de consultas.py.

Separado das consultas porque são responsabilidades distintas:
`consultas.py` sabe SQL e não sabe o que o dashboard mostra; este módulo
sabe o que o dashboard mostra e não escreve SQL. Trocar a origem dos
dados (vista materializada, cache) não deveria tocar aqui.

Os oito recortes abaixo são os da seção 5 de docs/Arquitetura.md, e
cada um existe porque habilita uma decisão — não porque o dado estava
disponível.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class Janela(Enum):
    """Períodos oferecidos pelo dashboard."""

    ULTIMOS_7_DIAS = "7d"
    ULTIMOS_30_DIAS = "30d"
    ULTIMOS_90_DIAS = "90d"

    def intervalo(self, agora: datetime) -> tuple[datetime, datetime]:
        """Converte a janela em (inicio, fim) concretos."""
        raise NotImplementedError("Cálculo de janela a implementar na onda 4")


@dataclass(frozen=True)
class ResumoSeguranca:
    """Cabeçalho do recorte de segurança do dashboard."""

    total_mensagens: int
    bloqueios_injecao: int
    bloqueios_abuso: int
    bloqueios_saida: int

    @property
    def taxa_de_bloqueio(self) -> float:
        """Proporção de mensagens barradas, entre 0.0 e 1.0."""
        if self.total_mensagens == 0:
            return 0.0
        barradas = self.bloqueios_injecao + self.bloqueios_abuso + self.bloqueios_saida
        return barradas / self.total_mensagens


@dataclass(frozen=True)
class ResumoCatalogo:
    """Cabeçalho do recorte de evolução do catálogo."""

    intencoes_acionadas: int
    intencoes_sem_uso: int  # classes do catálogo que ninguém acionou
    enunciados_fora_de_escopo: int
    enunciados_baixa_confianca: int


async def resumo_de_seguranca(janela: Janela) -> ResumoSeguranca:
    """Números do topo do recorte de segurança."""
    raise NotImplementedError("Métricas a implementar na onda 4")


async def resumo_de_catalogo(janela: Janela) -> ResumoCatalogo:
    """Números do topo do recorte de evolução do catálogo."""
    raise NotImplementedError("Métricas a implementar na onda 4")
