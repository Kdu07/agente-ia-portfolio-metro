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
from app.pipeline.orquestrador import ETAPAS
from app.schemas.usuario import Perfil

# Nome legível de cada intenção do catálogo, como aparece no eixo do
# gráfico. O id técnico continua sendo a chave; o rótulo é só exibição.
# Um id sem entrada aqui — uma intenção nova ainda não rotulada, ou uma
# antiga que saiu do catálogo — recebe um rótulo derivado do próprio id,
# e não some do gráfico.
ROTULO_DE_INTENCAO: dict[str, str] = {
    "consultar_status_projeto": "Consultar status de projeto",
    "consultar_avanco": "Consultar avanço",
    "consultar_cronograma": "Consultar cronograma",
    "consultar_marcos": "Consultar marcos",
    "consultar_riscos": "Consultar riscos",
    "consultar_problemas": "Consultar problemas",
    "consultar_aderencia_normativa": "Consultar aderência normativa",
    "consultar_documento_projeto": "Consultar documento do projeto",
    "consultar_conceito_gestao": "Consultar conceito de gestão",
    "consultar_faturas_vencidas": "Consultar faturas vencidas",
    "comparar_projetos": "Comparar projetos",
    "consultar_indicadores_portfolio": "Consultar indicadores do portfólio",
    "gerar_relatorio_status": "Gerar relatório de status",
    "gerar_previa_diretoria": "Gerar prévia para a diretoria",
    "gerar_relatorio_encerramento": "Gerar relatório de encerramento",
    "criar_projeto": "Criar projeto",
    "atualizar_avanco": "Atualizar avanço",
    "atualizar_cronograma": "Atualizar cronograma",
    "registrar_risco": "Registrar risco",
    "registrar_problema": "Registrar problema",
    "atualizar_termo_abertura": "Atualizar termo de abertura",
    "registrar_entrega_marco": "Registrar entrega de marco",
    "atualizar_mapa_beneficios": "Atualizar mapa de benefícios",
    "registrar_mudanca": "Registrar mudança",
    "encerrar_projeto": "Encerrar projeto",
    "consultar_pendencias": "Consultar pendências",
}

# Rótulos do painel para cada desfecho. Diferentes dos da bolha do chat
# de propósito: lá o leitor é quem teve a mensagem recusada, e o rótulo
# não deve ensinar qual barreira a pegou; aqui o leitor tem
# `ver_intencoes` e precisa justamente dessa distinção para agir.
ROTULO_DE_DESFECHO: dict[Desfecho, str] = {
    Desfecho.ENCAMINHADA: "Atendida",
    Desfecho.BLOQUEADA_INJECAO_REGRA: "Bloqueada por regra",
    Desfecho.BLOQUEADA_INJECAO_MODELO: "Bloqueada por modelo",
    Desfecho.BLOQUEADA_ABUSO: "Bloqueada por uso indevido",
    Desfecho.RECUSADA_FORA_ESCOPO: "Fora do escopo",
    Desfecho.RECUSADA_BAIXA_CONFIANCA: "Baixa confiança",
    Desfecho.BLOQUEADA_SAIDA: "Resposta não entregue",
    Desfecho.FALHA_EXECUTOR: "Falha do executor",
}


def rotulo_de_intencao(intencao_id: str) -> str:
    """Nome legível da intenção, derivado do id quando não há rótulo."""
    rotulo = ROTULO_DE_INTENCAO.get(intencao_id)
    if rotulo is not None:
        return rotulo
    return intencao_id.replace("_", " ").capitalize()


def rotulo_de_desfecho(desfecho: str) -> str:
    """Nome legível do desfecho, a partir do valor gravado."""
    return ROTULO_DE_DESFECHO[Desfecho(desfecho)]


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


@dataclass(frozen=True)
class LatenciaEtapa:
    """Percentis de uma etapa do pipeline, em milissegundos."""

    etapa: str
    p50: float
    p95: float
    amostras: int  # mensagens que chegaram a percorrer a etapa


@dataclass(frozen=True)
class LatenciaPipeline:
    """Latência total e decomposta por etapa."""

    p50: float
    p95: float
    etapas: list[LatenciaEtapa]


async def latencia_do_pipeline(
    sessao: AsyncSession,
    janela: Janela,
    *,
    agora: datetime | None = None,
    perfil: Perfil | None = None,
) -> LatenciaPipeline:
    """Percentis do pipeline inteiro e de cada etapa.

    É o indicador computacional que a seção 3.1.5 do Projeto.md declara
    como métrica do pipeline de PLN: o total diz quanto custa o pedágio,
    e a decomposição diz qual barreira o cobra.

    Todas as etapas do orquestrador aparecem, na ordem em que rodam,
    mesmo sem amostra. `amostras` distingue "rápida" de "não percorrida":
    uma etapa com p95 zero e nenhuma amostra não foi exercitada na
    janela, e não é gratuita. Os percentis de cada etapa são calculados
    só sobre as mensagens que chegaram a ela, e por isso não se somam
    para dar o total — o executor de uma mensagem encaminhada não se
    soma à injeção de outra que foi barrada.
    """
    inicio, fim = janela.intervalo(agora)
    total = await consultas.latencia(sessao, inicio, fim, perfil=perfil)
    amostras = await consultas.amostras_de_latencia_por_etapa(sessao, inicio, fim, perfil=perfil)
    etapas = list(ETAPAS) + sorted(etapa for etapa in amostras if etapa not in ETAPAS)
    return LatenciaPipeline(
        p50=total["p50"],
        p95=total["p95"],
        etapas=[
            LatenciaEtapa(
                etapa=etapa,
                p50=consultas.percentil(amostras.get(etapa, []), 0.5),
                p95=consultas.percentil(amostras.get(etapa, []), 0.95),
                amostras=len(amostras.get(etapa, [])),
            )
            for etapa in etapas
        ],
    )
