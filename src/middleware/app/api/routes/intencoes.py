"""Dashboard de análise de intenções.

TODAS as rotas deste módulo exigem `Permissao.VER_INTENCOES`, aplicada no
router inteiro e não rota a rota: uma rota nova aqui nasce protegida por
padrão. Esquecer o decorador numa rota individual é o tipo de erro que
não aparece em teste funcional e vaza o histórico de todo mundo.

O que se vê aqui é o agregado de todos os usuários, incluindo os prompts
em claro nos recortes de recusa. É por isso que a permissão é separada do
perfil: ver o dashboard não decorre de ser diretor.
"""

from fastapi import APIRouter, Depends

from app.analytics.metricas import Janela
from app.api.deps import exige_permissao
from app.schemas.intencao import (
    ContagemResposta,
    EnunciadoAgrupadoResposta,
    LatenciaResposta,
    ResumoCatalogoResposta,
    ResumoSegurancaResposta,
    SerieResposta,
)
from app.schemas.usuario import Permissao

router = APIRouter(
    prefix="/intencoes",
    dependencies=[Depends(exige_permissao(Permissao.VER_INTENCOES))],
)


@router.get("/volume", response_model=list[ContagemResposta])
async def volume_por_intencao(janela: Janela = Janela.ULTIMOS_30_DIAS):
    """Mensagens por intenção, incluindo as classes com contagem zero."""
    raise NotImplementedError("Dashboard a implementar na onda 4")


@router.get("/desfechos", response_model=list[ContagemResposta])
async def distribuicao_de_desfechos(janela: Janela = Janela.ULTIMOS_30_DIAS):
    """Quanto foi atendido, bloqueado, recusado e falhou."""
    raise NotImplementedError("Dashboard a implementar na onda 4")


@router.get("/seguranca/resumo", response_model=ResumoSegurancaResposta)
async def resumo_de_seguranca(janela: Janela = Janela.ULTIMOS_30_DIAS):
    """Cabeçalho do recorte de segurança."""
    raise NotImplementedError("Dashboard a implementar na onda 4")


@router.get("/seguranca/serie", response_model=list[SerieResposta])
async def serie_de_bloqueios(janela: Janela = Janela.ULTIMOS_30_DIAS):
    """Bloqueios ao longo do tempo, uma linha por guarda.

    Injeção, abuso e saída em séries separadas: um pico em injeção é
    incidente de segurança e um pico em abuso é problema de uso. Somá-los
    num único número esconderia os dois.
    """
    raise NotImplementedError("Dashboard a implementar na onda 4")


@router.get("/catalogo/resumo", response_model=ResumoCatalogoResposta)
async def resumo_de_catalogo(janela: Janela = Janela.ULTIMOS_30_DIAS):
    """Cabeçalho do recorte de evolução do catálogo."""
    raise NotImplementedError("Dashboard a implementar na onda 4")


@router.get("/catalogo/fora-de-escopo", response_model=list[EnunciadoAgrupadoResposta])
async def enunciados_fora_de_escopo(janela: Janela = Janela.ULTIMOS_30_DIAS):
    """O que os usuários pedem e o agente não faz.

    É o backlog de novas intenções, e o ponto onde o ciclo
    registro -> análise -> catálogo se fecha.
    """
    raise NotImplementedError("Dashboard a implementar na onda 4")


@router.get("/catalogo/baixa-confianca", response_model=list[EnunciadoAgrupadoResposta])
async def enunciados_baixa_confianca(janela: Janela = Janela.ULTIMOS_30_DIAS):
    """Onde o classificador hesita — candidatos a mais exemplos de treino."""
    raise NotImplementedError("Dashboard a implementar na onda 4")


@router.get("/latencia", response_model=LatenciaResposta)
async def latencia(janela: Janela = Janela.ULTIMOS_30_DIAS):
    """Percentis p50 e p95 do pipeline — o custo do pedágio, medido."""
    raise NotImplementedError("Dashboard a implementar na onda 4")
