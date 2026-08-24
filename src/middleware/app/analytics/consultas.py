"""Agregações SQL sobre o registro de interações.

Camada de acesso do dashboard. Para o volume esperado de um MVP,
agregação direta sobre a tabela `interacao` é suficiente, com índices em:

    (criada_em)
    (intencao_id, criada_em)
    (desfecho, criada_em)

Vista materializada apenas se o dashboard começar a pesar — não
antecipar. O custo de manter uma vista sincronizada supera o ganho
enquanto o volume couber num índice.

Todas as funções recebem uma janela (`inicio`, `fim`) explícita. Nenhuma
consulta varre a tabela inteira por padrão: um dashboard aberto sem
filtro não deve conseguir derrubar o banco.
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class ContagemPorChave:
    """Uma linha de contagem agrupada (intenção, desfecho, perfil, canal)."""

    chave: str
    total: int


@dataclass(frozen=True)
class PontoSerie:
    """Um ponto de uma série temporal."""

    momento: datetime
    total: int


@dataclass(frozen=True)
class EnunciadoAgrupado:
    """Um enunciado recusado e quantas vezes apareceu.

    Alimenta o backlog de novas intenções: é a matéria-prima do ciclo
    registro -> análise -> catálogo.
    """

    prompt: str
    ocorrencias: int
    ultima_em: datetime
    confianca_media: float


async def volume_por_intencao(
    inicio: datetime, fim: datetime
) -> list[ContagemPorChave]:
    """Quantas mensagens por intenção na janela.

    Inclui as intenções com contagem zero: uma classe do catálogo que
    nunca é acionada é achado, não ausência de dado, e sumir da lista
    esconderia justamente isso.
    """
    raise NotImplementedError("Agregações a implementar na onda 4")


async def distribuicao_de_desfechos(
    inicio: datetime, fim: datetime
) -> list[ContagemPorChave]:
    """Quanto foi atendido, bloqueado, recusado e falhou."""
    raise NotImplementedError("Agregações a implementar na onda 4")


async def serie_de_bloqueios(
    inicio: datetime, fim: datetime, *, granularidade: str = "dia"
) -> dict[str, list[PontoSerie]]:
    """Série temporal de bloqueios, uma linha por guarda.

    Separa injeção de abuso de saída de propósito: um pico em injeção é
    incidente de segurança e um pico em abuso é problema de uso. Somá-los
    num único número esconderia os dois.
    """
    raise NotImplementedError("Agregações a implementar na onda 4")


async def enunciados_fora_de_escopo(
    inicio: datetime, fim: datetime, *, limite: int = 50
) -> list[EnunciadoAgrupado]:
    """O que os usuários pedem e o agente não faz — backlog do catálogo."""
    raise NotImplementedError("Agregações a implementar na onda 4")


async def enunciados_baixa_confianca(
    inicio: datetime, fim: datetime, *, limite: int = 50
) -> list[EnunciadoAgrupado]:
    """Onde o classificador hesita — candidatos a mais exemplos de treino."""
    raise NotImplementedError("Agregações a implementar na onda 4")


async def confianca_media_por_intencao(
    inicio: datetime, fim: datetime
) -> dict[str, float]:
    """Confiança média por intenção; aponta classes confundidas entre si.

    Complementa a matriz de confusão exigida pelo RNF03 com dados de uso
    real, e não apenas do conjunto de teste.
    """
    raise NotImplementedError("Agregações a implementar na onda 4")


async def volume_por_perfil_e_canal(
    inicio: datetime, fim: datetime
) -> list[ContagemPorChave]:
    """Como cada perfil usa o agente, e quanto entra por voz ou rotina."""
    raise NotImplementedError("Agregações a implementar na onda 4")


async def latencia(inicio: datetime, fim: datetime) -> dict[str, float]:
    """Percentis p50 e p95 da latência do pipeline, em milissegundos.

    É o custo do pedágio, medido. Sustenta o argumento de desempenho
    frente à latência extra assumida na seção 1.3 da Arquitetura.
    """
    raise NotImplementedError("Agregações a implementar na onda 4")
