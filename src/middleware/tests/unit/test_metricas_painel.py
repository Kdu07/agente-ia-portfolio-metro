"""Métricas do cartão-resumo e de latência do painel de intenções."""

from datetime import UTC, datetime, timedelta

import pytest

from app.analytics import consultas, metricas
from app.analytics.metricas import Janela
from app.pipeline import orquestrador as orq
from app.pipeline.desfechos import Desfecho
from app.pipeline.intencao import catalogo
from app.schemas.usuario import Perfil

AGORA = datetime(2026, 9, 21, 15, 0, tzinfo=UTC)
ONTEM = AGORA - timedelta(days=1)


# --- Janela -----------------------------------------------------------------


@pytest.mark.parametrize(
    ("janela", "dias"),
    [(Janela.ULTIMOS_7_DIAS, 7), (Janela.ULTIMOS_30_DIAS, 30), (Janela.ULTIMOS_90_DIAS, 90)],
)
def test_janela_recua_o_numero_de_dias_a_partir_de_agora(janela, dias):
    inicio, fim = janela.intervalo(AGORA)

    assert fim == AGORA
    assert fim - inicio == timedelta(days=dias)


def test_janela_sem_agora_termina_no_instante_atual():
    antes = datetime.now(UTC)
    _, fim = Janela.ULTIMOS_7_DIAS.intervalo()

    assert antes <= fim <= datetime.now(UTC)


def test_janela_recusa_instante_sem_fuso():
    with pytest.raises(ValueError, match="fuso"):
        Janela.ULTIMOS_7_DIAS.intervalo(AGORA.replace(tzinfo=None))


# --- Resumo de segurança ------------------------------------------------------


async def test_resumo_de_seguranca_separa_as_tres_guardas(banco_analitico, registrar):
    await registrar(criada_em=ONTEM)
    await registrar(criada_em=ONTEM, intencao_id=None, desfecho=Desfecho.BLOQUEADA_INJECAO_REGRA)
    await registrar(criada_em=ONTEM, desfecho=Desfecho.BLOQUEADA_INJECAO_MODELO)
    await registrar(criada_em=ONTEM, intencao_id=None, desfecho=Desfecho.BLOQUEADA_ABUSO)
    await registrar(criada_em=ONTEM, desfecho=Desfecho.BLOQUEADA_SAIDA)
    await registrar(criada_em=ONTEM, desfecho=Desfecho.RECUSADA_FORA_ESCOPO)

    resumo = await metricas.resumo_de_seguranca(banco_analitico, Janela.ULTIMOS_7_DIAS, agora=AGORA)

    assert resumo.total_mensagens == 6
    assert resumo.bloqueios_injecao == 2
    assert resumo.bloqueios_abuso == 1
    assert resumo.bloqueios_saida == 1
    assert resumo.taxa_de_bloqueio == pytest.approx(4 / 6)


async def test_resumo_de_seguranca_sem_mensagens_tem_taxa_zero(banco_analitico):
    resumo = await metricas.resumo_de_seguranca(banco_analitico, Janela.ULTIMOS_7_DIAS, agora=AGORA)

    assert resumo.total_mensagens == 0
    assert resumo.taxa_de_bloqueio == 0.0


async def test_resumo_de_seguranca_respeita_a_janela(banco_analitico, registrar):
    await registrar(criada_em=AGORA - timedelta(days=10), desfecho=Desfecho.BLOQUEADA_ABUSO)

    resumo_7 = await metricas.resumo_de_seguranca(
        banco_analitico, Janela.ULTIMOS_7_DIAS, agora=AGORA
    )
    resumo_30 = await metricas.resumo_de_seguranca(
        banco_analitico, Janela.ULTIMOS_30_DIAS, agora=AGORA
    )

    assert resumo_7.bloqueios_abuso == 0
    assert resumo_30.bloqueios_abuso == 1


async def test_resumo_de_seguranca_filtra_pelo_perfil(banco_analitico, registrar):
    await registrar(criada_em=ONTEM, perfil=Perfil.DIRETORIA)
    await registrar(criada_em=ONTEM, perfil=Perfil.MEMBRO_EQUIPE)

    resumo = await metricas.resumo_de_seguranca(
        banco_analitico, Janela.ULTIMOS_7_DIAS, agora=AGORA, perfil=Perfil.DIRETORIA
    )

    assert resumo.total_mensagens == 1


# --- Resumo de catálogo -------------------------------------------------------


async def test_resumo_de_catalogo_conta_classes_acionadas_e_sem_uso(banco_analitico, registrar):
    await registrar(criada_em=ONTEM, intencao_id="consultar_status_projeto")
    await registrar(criada_em=ONTEM, intencao_id="consultar_status_projeto")
    await registrar(criada_em=ONTEM, intencao_id="consultar_riscos")
    await registrar(
        criada_em=ONTEM,
        intencao_id=catalogo.FORA_DE_ESCOPO,
        desfecho=Desfecho.RECUSADA_FORA_ESCOPO,
    )
    await registrar(criada_em=ONTEM, desfecho=Desfecho.RECUSADA_BAIXA_CONFIANCA)

    resumo = await metricas.resumo_de_catalogo(banco_analitico, Janela.ULTIMOS_7_DIAS, agora=AGORA)

    total_catalogo = len(consultas.intencoes_acionaveis())
    assert resumo.intencoes_acionadas == 2
    assert resumo.intencoes_sem_uso == total_catalogo - 2
    assert resumo.enunciados_fora_de_escopo == 1
    assert resumo.enunciados_baixa_confianca == 1


async def test_resumo_de_catalogo_nao_cobra_uso_de_intencao_removida(banco_analitico, registrar):
    await registrar(criada_em=ONTEM, intencao_id="intencao_removida")

    resumo = await metricas.resumo_de_catalogo(banco_analitico, Janela.ULTIMOS_7_DIAS, agora=AGORA)

    assert resumo.intencoes_acionadas == 1
    assert resumo.intencoes_sem_uso == len(consultas.intencoes_acionaveis())


# --- Latência por etapa -------------------------------------------------------


async def test_latencia_por_etapa_calcula_percentis_de_cada_etapa(banco_analitico, registrar):
    for executor in (1000, 2000, 3000):
        await registrar(
            criada_em=ONTEM,
            latencia_ms=executor + 100,
            latencia_etapas={"injecao": 40, "abuso": 20, "intencao": 30, "executor": executor},
        )

    resultado = await metricas.latencia_do_pipeline(
        banco_analitico, Janela.ULTIMOS_7_DIAS, agora=AGORA
    )

    por_etapa = {item.etapa: item for item in resultado.etapas}
    assert por_etapa["executor"].p50 == pytest.approx(2000)
    assert por_etapa["executor"].p95 == pytest.approx(2900)
    assert por_etapa["injecao"].p50 == pytest.approx(40)
    assert por_etapa["executor"].amostras == 3
    assert resultado.p50 == pytest.approx(2100)


async def test_latencia_por_etapa_lista_todas_as_etapas_na_ordem(banco_analitico):
    resultado = await metricas.latencia_do_pipeline(
        banco_analitico, Janela.ULTIMOS_7_DIAS, agora=AGORA
    )

    assert [item.etapa for item in resultado.etapas] == list(orq.ETAPAS)
    assert all(item.amostras == 0 for item in resultado.etapas)


async def test_latencia_por_etapa_so_conta_quem_percorreu_a_etapa(banco_analitico, registrar):
    await registrar(criada_em=ONTEM, latencia_etapas={"injecao": 15})
    await registrar(
        criada_em=ONTEM,
        latencia_etapas={"injecao": 25, "abuso": 10, "intencao": 5, "executor": 900, "saida": 50},
    )

    resultado = await metricas.latencia_do_pipeline(
        banco_analitico, Janela.ULTIMOS_7_DIAS, agora=AGORA
    )

    por_etapa = {item.etapa: item for item in resultado.etapas}
    assert por_etapa["injecao"].amostras == 2
    assert por_etapa["executor"].amostras == 1
    assert por_etapa["executor"].p50 == pytest.approx(900)


async def test_latencia_por_etapa_ignora_interacoes_anteriores_a_medicao(
    banco_analitico, registrar
):
    await registrar(criada_em=ONTEM, latencia_ms=5000)

    resultado = await metricas.latencia_do_pipeline(
        banco_analitico, Janela.ULTIMOS_7_DIAS, agora=AGORA
    )

    assert resultado.p50 == pytest.approx(5000)
    assert all(item.amostras == 0 for item in resultado.etapas)


# --- Rótulos ------------------------------------------------------------------


def test_toda_intencao_acionavel_tem_rotulo_proprio():
    """Uma intenção nova no catálogo precisa ganhar nome no painel."""
    sem_rotulo = set(consultas.intencoes_acionaveis()) - set(metricas.ROTULO_DE_INTENCAO)
    assert sem_rotulo == set()


def test_intencao_sem_rotulo_recebe_nome_derivado_do_id():
    assert metricas.rotulo_de_intencao("intencao_antiga") == "Intencao antiga"


def test_todo_desfecho_tem_rotulo():
    assert set(metricas.ROTULO_DE_DESFECHO) == set(Desfecho)
    assert metricas.rotulo_de_desfecho("bloqueada_abuso") == "Bloqueada por uso indevido"
