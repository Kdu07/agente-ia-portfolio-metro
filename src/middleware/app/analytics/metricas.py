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
from datetime import UTC, datetime, timedelta
from enum import Enum

from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics import consultas
from app.pipeline.desfechos import Desfecho
from app.schemas.usuario import Perfil


class Janela(Enum):
    """Períodos oferecidos pelo dashboard."""

    ULTIMOS_7_DIAS = "7d"
    ULTIMOS_30_DIAS = "30d"
    ULTIMOS_90_DIAS = "90d"

    @property
    def dias(self) -> int:
        """Extensão da janela em dias."""
        return int(self.value.removesuffix("d"))

    def intervalo(self, agora: datetime | None = None) -> tuple[datetime, datetime]:
        """Converte a janela em (inicio, fim) concretos.

        A janela termina agora e recua um número fixo de dias, em vez de
        começar à meia-noite: "últimos 7 dias" aberto às 15h compara com
        o mesmo horário da semana anterior, e o primeiro dia não aparece
        pela metade. O fim é o instante da consulta, para que a mensagem
        que acabou de ser registrada já apareça.
        """
        fim = agora if agora is not None else datetime.now(UTC)
        if fim.tzinfo is None:
            raise ValueError("`agora` precisa de fuso: um instante ingênuo é ambíguo")
        return fim - timedelta(days=self.dias), fim


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


async def resumo_de_seguranca(
    sessao: AsyncSession,
    janela: Janela,
    *,
    agora: datetime | None = None,
    perfil: Perfil | None = None,
) -> ResumoSeguranca:
    """Números do topo do recorte de segurança.

    Parte da distribuição de desfechos, e não de três contagens
    próprias, para que o cartão e o gráfico ao lado leiam a mesma
    consulta e nunca mostrem números que não fecham entre si. A injeção
    soma regra e modelo, que são camadas da mesma guarda; as três
    guardas continuam separadas.
    """
    inicio, fim = janela.intervalo(agora)
    contagens = {
        linha.chave: linha.total
        for linha in await consultas.distribuicao_de_desfechos(sessao, inicio, fim, perfil=perfil)
    }
    return ResumoSeguranca(
        total_mensagens=sum(contagens.values()),
        bloqueios_injecao=contagens[Desfecho.BLOQUEADA_INJECAO_REGRA.value]
        + contagens[Desfecho.BLOQUEADA_INJECAO_MODELO.value],
        bloqueios_abuso=contagens[Desfecho.BLOQUEADA_ABUSO.value],
        bloqueios_saida=contagens[Desfecho.BLOQUEADA_SAIDA.value],
    )


async def resumo_de_catalogo(
    sessao: AsyncSession,
    janela: Janela,
    *,
    agora: datetime | None = None,
    perfil: Perfil | None = None,
) -> ResumoCatalogo:
    """Números do topo do recorte de evolução do catálogo.

    `intencoes_sem_uso` conta só as classes que o catálogo atual
    reconhece: um id antigo, já removido numa revisão, aparece no volume
    quando foi usado, mas não pode ser cobrado como "sem uso" depois de
    deixar de existir.
    """
    inicio, fim = janela.intervalo(agora)
    volume = await consultas.volume_por_intencao(sessao, inicio, fim, perfil=perfil)
    desfechos = {
        linha.chave: linha.total
        for linha in await consultas.distribuicao_de_desfechos(sessao, inicio, fim, perfil=perfil)
    }
    vigentes = set(consultas.intencoes_acionaveis())
    return ResumoCatalogo(
        intencoes_acionadas=sum(1 for linha in volume if linha.total > 0),
        intencoes_sem_uso=sum(
            1 for linha in volume if linha.total == 0 and linha.chave in vigentes
        ),
        enunciados_fora_de_escopo=desfechos[Desfecho.RECUSADA_FORA_ESCOPO.value],
        enunciados_baixa_confianca=desfechos[Desfecho.RECUSADA_BAIXA_CONFIANCA.value],
    )
