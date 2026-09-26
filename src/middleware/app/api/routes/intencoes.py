"""Dashboard de análise de intenções.

TODAS as rotas deste módulo exigem `Permissao.VER_INTENCOES`, aplicada no
router inteiro e não rota a rota: uma rota nova aqui nasce protegida por
padrão. Esquecer o decorador numa rota individual é o tipo de erro que
não aparece em teste funcional e vaza o histórico de todo mundo.

O que se vê aqui é o agregado de todos os usuários, incluindo os prompts
em claro nos recortes de recusa. É por isso que a permissão é separada do
perfil: ver o dashboard não decorre de ser diretor.

As rotas não calculam nada: convertem a janela em intervalo, delegam a
`analytics/` e traduzem o resultado para o contrato de
`schemas/intencao.py`. O filtro opcional `perfil` recorta pelo perfil
gravado na interação — ver a docstring de analytics/consultas.py.
"""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends

from app.analytics import consultas, metricas
from app.analytics.metricas import Janela
from app.api.deps import SessaoBanco, exige_permissao
from app.schemas.intencao import (
    ContagemResposta,
    EnunciadoAgrupadoResposta,
    LatenciaEtapaResposta,
    LatenciaResposta,
    PontoSerieResposta,
    ResumoCatalogoResposta,
    ResumoSegurancaResposta,
    SerieResposta,
)
from app.schemas.usuario import Perfil, Permissao

router = APIRouter(
    prefix="/intencoes",
    dependencies=[Depends(exige_permissao(Permissao.VER_INTENCOES))],
)

JANELA_PADRAO = Janela.ULTIMOS_30_DIAS


def _intervalo(janela: Janela) -> tuple[datetime, datetime]:
    """Intervalo concreto da janela, terminando no instante da requisição."""
    return janela.intervalo(datetime.now(UTC))


def _enunciados(linhas: list[consultas.EnunciadoAgrupado]) -> list[EnunciadoAgrupadoResposta]:
    return [
        EnunciadoAgrupadoResposta(
            prompt=linha.prompt,
            ocorrencias=linha.ocorrencias,
            ultima_em=linha.ultima_em,
            confianca_media=linha.confianca_media,
        )
        for linha in linhas
    ]


@router.get("/volume", response_model=list[ContagemResposta])
async def volume_por_intencao(
    sessao: SessaoBanco,
    janela: Janela = JANELA_PADRAO,
    perfil: Perfil | None = None,
) -> list[ContagemResposta]:
    """Mensagens por intenção, incluindo as classes com contagem zero."""
    inicio, fim = _intervalo(janela)
    linhas = await consultas.volume_por_intencao(sessao, inicio, fim, perfil=perfil)
    return [
        ContagemResposta(
            chave=linha.chave,
            rotulo=metricas.rotulo_de_intencao(linha.chave),
            total=linha.total,
        )
        for linha in linhas
    ]


@router.get("/desfechos", response_model=list[ContagemResposta])
async def distribuicao_de_desfechos(
    sessao: SessaoBanco,
    janela: Janela = JANELA_PADRAO,
    perfil: Perfil | None = None,
) -> list[ContagemResposta]:
    """Quanto foi atendido, bloqueado, recusado e falhou."""
    inicio, fim = _intervalo(janela)
    linhas = await consultas.distribuicao_de_desfechos(sessao, inicio, fim, perfil=perfil)
    return [
        ContagemResposta(
            chave=linha.chave,
            rotulo=metricas.rotulo_de_desfecho(linha.chave),
            total=linha.total,
        )
        for linha in linhas
    ]


@router.get("/seguranca/resumo", response_model=ResumoSegurancaResposta)
async def resumo_de_seguranca(
    sessao: SessaoBanco,
    janela: Janela = JANELA_PADRAO,
    perfil: Perfil | None = None,
) -> ResumoSegurancaResposta:
    """Cabeçalho do recorte de segurança."""
    resumo = await metricas.resumo_de_seguranca(sessao, janela, perfil=perfil)
    return ResumoSegurancaResposta(
        total_mensagens=resumo.total_mensagens,
        bloqueios_injecao=resumo.bloqueios_injecao,
        bloqueios_abuso=resumo.bloqueios_abuso,
        bloqueios_saida=resumo.bloqueios_saida,
        taxa_de_bloqueio=resumo.taxa_de_bloqueio,
    )


@router.get("/seguranca/serie", response_model=list[SerieResposta])
async def serie_de_bloqueios(
    sessao: SessaoBanco,
    janela: Janela = JANELA_PADRAO,
    perfil: Perfil | None = None,
) -> list[SerieResposta]:
    """Bloqueios ao longo do tempo, uma linha por guarda.

    Injeção, abuso e saída em séries separadas: um pico em injeção é
    incidente de segurança e um pico em abuso é problema de uso. Somá-los
    num único número esconderia os dois.
    """
    inicio, fim = _intervalo(janela)
    series = await consultas.serie_de_bloqueios(sessao, inicio, fim, perfil=perfil)
    return [
        SerieResposta(
            nome=guarda,
            pontos=[PontoSerieResposta(momento=p.momento, total=p.total) for p in pontos],
        )
        for guarda, pontos in series.items()
    ]


@router.get("/catalogo/resumo", response_model=ResumoCatalogoResposta)
async def resumo_de_catalogo(
    sessao: SessaoBanco,
    janela: Janela = JANELA_PADRAO,
    perfil: Perfil | None = None,
) -> ResumoCatalogoResposta:
    """Cabeçalho do recorte de evolução do catálogo."""
    resumo = await metricas.resumo_de_catalogo(sessao, janela, perfil=perfil)
    return ResumoCatalogoResposta(
        intencoes_acionadas=resumo.intencoes_acionadas,
        intencoes_sem_uso=resumo.intencoes_sem_uso,
        enunciados_fora_de_escopo=resumo.enunciados_fora_de_escopo,
        enunciados_baixa_confianca=resumo.enunciados_baixa_confianca,
    )


@router.get("/catalogo/fora-de-escopo", response_model=list[EnunciadoAgrupadoResposta])
async def enunciados_fora_de_escopo(
    sessao: SessaoBanco,
    janela: Janela = JANELA_PADRAO,
    perfil: Perfil | None = None,
) -> list[EnunciadoAgrupadoResposta]:
    """O que os usuários pedem e o agente não faz.

    É o backlog de novas intenções, e o ponto onde o ciclo
    registro -> análise -> catálogo se fecha.
    """
    inicio, fim = _intervalo(janela)
    return _enunciados(
        await consultas.enunciados_fora_de_escopo(sessao, inicio, fim, perfil=perfil)
    )


@router.get("/catalogo/baixa-confianca", response_model=list[EnunciadoAgrupadoResposta])
async def enunciados_baixa_confianca(
    sessao: SessaoBanco,
    janela: Janela = JANELA_PADRAO,
    perfil: Perfil | None = None,
) -> list[EnunciadoAgrupadoResposta]:
    """Onde o classificador hesita — candidatos a mais exemplos de treino."""
    inicio, fim = _intervalo(janela)
    return _enunciados(
        await consultas.enunciados_baixa_confianca(sessao, inicio, fim, perfil=perfil)
    )


@router.get("/latencia", response_model=LatenciaResposta)
async def latencia(
    sessao: SessaoBanco,
    janela: Janela = JANELA_PADRAO,
    perfil: Perfil | None = None,
) -> LatenciaResposta:
    """Percentis p50 e p95 do pipeline — o custo do pedágio, medido.

    Além do total, decompõe o tempo por etapa percorrida, para que o
    painel aponte qual barreira pesa.
    """
    resultado = await metricas.latencia_do_pipeline(sessao, janela, perfil=perfil)
    return LatenciaResposta(
        p50=resultado.p50,
        p95=resultado.p95,
        etapas=[
            LatenciaEtapaResposta(
                etapa=item.etapa, p50=item.p50, p95=item.p95, amostras=item.amostras
            )
            for item in resultado.etapas
        ],
    )
