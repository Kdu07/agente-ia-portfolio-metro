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
filtro não deve conseguir derrubar o banco. A janela é semiaberta —
inclui `inicio`, exclui `fim` — para que duas janelas consecutivas não
contem a mesma interação duas vezes.

O recorte opcional por `perfil` usa o perfil gravado NA interação, e
não o atual do usuário: é o dado de auditoria descrito em
`InteracaoTabela`, e a pergunta do painel é "como a diretoria usou o
agente naquele período", não "o que fazem hoje os atuais diretores".

As consultas se restringem a SQL portável (`COUNT`, `AVG`, `MAX`,
`GROUP BY`, `lower`, `trim`). É essa restrição que permite exercitá-las
num SQLite em memória nos testes unitários. O que dependeria de função
específica do PostgreSQL — o truncamento de datas no fuso e os
percentis — é feito em Python sobre um recorte já pequeno, conforme a
justificativa de cada função.
"""

from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.persistence.tabelas import InteracaoTabela
from app.pipeline.desfechos import Desfecho
from app.pipeline.intencao import catalogo
from app.schemas.usuario import Perfil

_I = InteracaoTabela

# Fuso em que os pontos da série são agrupados. O painel é lido por
# quem opera em São Paulo, e um bloqueio às 22h de segunda precisa cair
# na segunda — em UTC, cairia na terça.
FUSO_DO_PAINEL = ZoneInfo("America/Sao_Paulo")

# A guarda que produziu cada desfecho de bloqueio. As duas camadas da
# guarda de injeção compartilham a linha; guardas diferentes, nunca.
GUARDA_POR_DESFECHO: dict[Desfecho, str] = {
    Desfecho.BLOQUEADA_INJECAO_REGRA: "injecao",
    Desfecho.BLOQUEADA_INJECAO_MODELO: "injecao",
    Desfecho.BLOQUEADA_ABUSO: "abuso",
    Desfecho.BLOQUEADA_SAIDA: "saida",
}
GUARDAS: tuple[str, ...] = ("injecao", "abuso", "saida")


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


def _na_janela(consulta: Select, inicio: datetime, fim: datetime, perfil: Perfil | None) -> Select:
    """Restringe a consulta à janela e, se informado, ao perfil.

    Uma janela invertida ou vazia é erro de quem chamou, e não resultado
    vazio: devolver zeros esconderia o defeito no cálculo da janela.
    """
    if fim <= inicio:
        raise ValueError(f"Janela inválida: fim ({fim}) não é posterior a inicio ({inicio})")
    consulta = consulta.where(_I.criada_em >= inicio, _I.criada_em < fim)
    if perfil is not None:
        consulta = consulta.where(_I.perfil == perfil.value)
    return consulta


def _em_utc(momento: datetime) -> datetime:
    """Devolve o instante com fuso UTC explícito.

    O PostgreSQL devolve `timestamptz` já com fuso; o SQLite dos testes
    devolve o valor sem fuso, gravado em UTC. Normalizar aqui mantém as
    duas origens indistinguíveis para quem consome o resultado.
    """
    if momento.tzinfo is None:
        return momento.replace(tzinfo=UTC)
    return momento.astimezone(UTC)


def intencoes_acionaveis() -> list[str]:
    """Ids do catálogo que o painel acompanha, na ordem do catálogo.

    As duas classes negativas ficam de fora: `fora_de_escopo` e
    `tentativa_injecao` são desfechos de recusa e de bloqueio, e já
    aparecem na distribuição de desfechos e na série de segurança.
    Contá-las também como intenção faria o mesmo evento pesar duas vezes
    no painel.
    """
    return [
        intencao.id
        for intencao in catalogo.CATALOGO.values()
        if intencao.categoria is not catalogo.Categoria.CLASSE_NEGATIVA
    ]


async def volume_por_intencao(
    sessao: AsyncSession,
    inicio: datetime,
    fim: datetime,
    *,
    perfil: Perfil | None = None,
) -> list[ContagemPorChave]:
    """Quantas mensagens por intenção na janela.

    Inclui as intenções com contagem zero: uma classe do catálogo que
    nunca é acionada é achado, não ausência de dado, e sumir da lista
    esconderia justamente isso.

    A lista parte do catálogo, e não do banco, porque é o catálogo que
    sabe quais classes existem; o banco só sabe quais foram acionadas. Um
    id gravado que o catálogo já não reconhece — uma intenção renomeada
    ou removida numa revisão — também aparece, para que a revisão não
    apague do painel o uso que a antecedeu.

    Ordenada do maior para o menor volume; empates mantêm a ordem do
    catálogo, o que deixa o resultado estável entre duas consultas.
    """
    consulta = (
        select(_I.intencao_id, func.count())
        .where(_I.intencao_id.is_not(None))
        .group_by(_I.intencao_id)
    )
    linhas = await sessao.execute(_na_janela(consulta, inicio, fim, perfil))
    contagens: dict[str, int] = {chave: total for chave, total in linhas.all()}

    negativas = {catalogo.FORA_DE_ESCOPO, catalogo.TENTATIVA_INJECAO}
    chaves = intencoes_acionaveis()
    chaves += sorted(chave for chave in contagens if chave not in chaves and chave not in negativas)
    resultado = [ContagemPorChave(chave, contagens.get(chave, 0)) for chave in chaves]
    return sorted(resultado, key=lambda linha: linha.total, reverse=True)


async def distribuicao_de_desfechos(
    sessao: AsyncSession,
    inicio: datetime,
    fim: datetime,
    *,
    perfil: Perfil | None = None,
) -> list[ContagemPorChave]:
    """Quanto foi atendido, bloqueado, recusado e falhou.

    Um item por valor de `Desfecho`, na ordem do enum e com zero quando
    não houve ocorrência. A ordem fixa importa para o gráfico: a cor de
    cada desfecho não pode trocar de posição de um período para outro.
    """
    consulta = select(_I.desfecho, func.count()).group_by(_I.desfecho)
    linhas = await sessao.execute(_na_janela(consulta, inicio, fim, perfil))
    contagens: dict[str, int] = {chave: total for chave, total in linhas.all()}
    return [ContagemPorChave(d.value, contagens.get(d.value, 0)) for d in Desfecho]


def _truncar(momento: datetime, granularidade: str) -> datetime:
    """Início do dia ou da hora que contém o instante, no fuso do painel."""
    local = _em_utc(momento).astimezone(FUSO_DO_PAINEL)
    if granularidade == "dia":
        return local.replace(hour=0, minute=0, second=0, microsecond=0)
    return local.replace(minute=0, second=0, microsecond=0)


def _baldes(inicio: datetime, fim: datetime, granularidade: str) -> list[datetime]:
    """Todos os intervalos da janela, inclusive os que não tiveram evento.

    O dia avança pelo calendário, e não somando 24 horas, para que um
    eventual horário de verão não desloque a meia-noite dos pontos.
    """
    baldes: list[datetime] = []
    atual = _truncar(inicio, granularidade)
    while atual < fim:
        baldes.append(atual)
        if granularidade == "dia":
            atual = datetime.combine(
                atual.date() + timedelta(days=1), time.min, tzinfo=FUSO_DO_PAINEL
            )
        else:
            atual = (atual.astimezone(UTC) + timedelta(hours=1)).astimezone(FUSO_DO_PAINEL)
    return baldes


async def serie_de_bloqueios(
    sessao: AsyncSession,
    inicio: datetime,
    fim: datetime,
    *,
    granularidade: str = "dia",
    perfil: Perfil | None = None,
) -> dict[str, list[PontoSerie]]:
    """Série temporal de bloqueios, uma linha por guarda.

    Separa injeção de abuso de saída de propósito: um pico em injeção é
    incidente de segurança e um pico em abuso é problema de uso. Somá-los
    num único número esconderia os dois. As duas camadas da guarda de
    injeção — regra e modelo — compõem a mesma linha, porque barram o
    mesmo tipo de evento; o que não se soma são guardas diferentes.

    Cada linha traz um ponto por intervalo da janela, com zero onde não
    houve bloqueio. Uma série que só tivesse os dias com evento ligaria
    dois picos distantes por uma reta, e o gráfico sugeriria atividade
    onde não houve nenhuma.

    O agrupamento por intervalo é feito em Python, e não com
    `date_trunc`: o truncamento precisa acontecer no fuso de quem lê o
    painel, e a função equivalente muda de nome e de semântica entre o
    PostgreSQL e o SQLite dos testes. O custo é pequeno porque só as
    linhas bloqueadas são lidas, e elas são uma fração do tráfego.
    """
    if granularidade not in ("dia", "hora"):
        raise ValueError(f"Granularidade desconhecida: {granularidade!r}")

    consulta = select(_I.desfecho, _I.criada_em).where(
        _I.desfecho.in_([desfecho.value for desfecho in GUARDA_POR_DESFECHO])
    )
    linhas = await sessao.execute(_na_janela(consulta, inicio, fim, perfil))

    contagens: dict[tuple[str, datetime], int] = {}
    for desfecho, criada_em in linhas.all():
        chave = (GUARDA_POR_DESFECHO[Desfecho(desfecho)], _truncar(criada_em, granularidade))
        contagens[chave] = contagens.get(chave, 0) + 1

    baldes = _baldes(inicio, fim, granularidade)
    return {
        guarda: [PontoSerie(balde, contagens.get((guarda, balde), 0)) for balde in baldes]
        for guarda in GUARDAS
    }


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


async def confianca_media_por_intencao(inicio: datetime, fim: datetime) -> dict[str, float]:
    """Confiança média por intenção; aponta classes confundidas entre si.

    Complementa a matriz de confusão exigida pelo RNF03 com dados de uso
    real, e não apenas do conjunto de teste.
    """
    raise NotImplementedError("Agregações a implementar na onda 4")


async def volume_por_perfil_e_canal(inicio: datetime, fim: datetime) -> list[ContagemPorChave]:
    """Como cada perfil usa o agente, e quanto entra por voz ou rotina."""
    raise NotImplementedError("Agregações a implementar na onda 4")


async def latencia(inicio: datetime, fim: datetime) -> dict[str, float]:
    """Percentis p50 e p95 da latência do pipeline, em milissegundos.

    É o custo do pedágio, medido. Sustenta o argumento de desempenho
    frente à latência extra assumida na seção 1.3 da Arquitetura.
    """
    raise NotImplementedError("Agregações a implementar na onda 4")
