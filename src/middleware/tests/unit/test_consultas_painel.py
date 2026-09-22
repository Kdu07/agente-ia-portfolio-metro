"""Agregações do painel de intenções, executadas sobre SQL de verdade.

O banco é o SQLite em memória de tests/unit/conftest.py. Cada teste
grava as interações que o distinguem e confere o agregado, e não a
consulta montada: o que importa ao painel é o número que chega, e a
forma do SQL pode mudar sem que isso seja defeito.
"""

from datetime import UTC, datetime, timedelta

import pytest

from app.analytics import consultas
from app.pipeline.desfechos import Desfecho
from app.pipeline.intencao import catalogo
from app.schemas.usuario import Perfil

FIM = datetime(2026, 9, 21, 12, 0, tzinfo=UTC)
INICIO = FIM - timedelta(days=7)
DENTRO = FIM - timedelta(days=1)


def _por_chave(linhas: list[consultas.ContagemPorChave]) -> dict[str, int]:
    return {linha.chave: linha.total for linha in linhas}


# --- Janela ---------------------------------------------------------------


async def test_janela_invertida_e_recusada(banco_analitico):
    with pytest.raises(ValueError, match="Janela inválida"):
        await consultas.volume_por_intencao(banco_analitico, FIM, INICIO)


async def test_janela_inclui_o_inicio_e_exclui_o_fim(banco_analitico, registrar):
    await registrar(criada_em=INICIO)
    await registrar(criada_em=FIM)
    await registrar(criada_em=INICIO - timedelta(seconds=1))

    linhas = await consultas.distribuicao_de_desfechos(banco_analitico, INICIO, FIM)

    assert _por_chave(linhas)[Desfecho.ENCAMINHADA.value] == 1


# --- Volume por intenção ----------------------------------------------------


async def test_volume_conta_mensagens_por_intencao(banco_analitico, registrar):
    for _ in range(3):
        await registrar(criada_em=DENTRO, intencao_id="consultar_status_projeto")
    await registrar(criada_em=DENTRO, intencao_id="consultar_riscos_projeto")

    volume = _por_chave(await consultas.volume_por_intencao(banco_analitico, INICIO, FIM))

    assert volume["consultar_status_projeto"] == 3
    assert volume["consultar_riscos_projeto"] == 1


async def test_volume_preserva_intencoes_com_contagem_zero(banco_analitico, registrar):
    await registrar(criada_em=DENTRO, intencao_id="consultar_status_projeto")

    volume = _por_chave(await consultas.volume_por_intencao(banco_analitico, INICIO, FIM))

    assert set(consultas.intencoes_acionaveis()) <= set(volume)
    zeradas = [chave for chave, total in volume.items() if total == 0]
    assert len(zeradas) == len(consultas.intencoes_acionaveis()) - 1


async def test_volume_sem_interacoes_devolve_o_catalogo_zerado(banco_analitico):
    volume = await consultas.volume_por_intencao(banco_analitico, INICIO, FIM)

    assert [linha.chave for linha in volume] == consultas.intencoes_acionaveis()
    assert all(linha.total == 0 for linha in volume)


async def test_volume_exclui_as_classes_negativas(banco_analitico, registrar):
    await registrar(
        criada_em=DENTRO,
        intencao_id=catalogo.FORA_DE_ESCOPO,
        desfecho=Desfecho.RECUSADA_FORA_ESCOPO,
    )
    await registrar(
        criada_em=DENTRO,
        intencao_id=catalogo.TENTATIVA_INJECAO,
        desfecho=Desfecho.BLOQUEADA_INJECAO_MODELO,
    )

    volume = _por_chave(await consultas.volume_por_intencao(banco_analitico, INICIO, FIM))

    assert catalogo.FORA_DE_ESCOPO not in volume
    assert catalogo.TENTATIVA_INJECAO not in volume


async def test_volume_mantem_intencao_que_saiu_do_catalogo(banco_analitico, registrar):
    await registrar(criada_em=DENTRO, intencao_id="intencao_renomeada")

    volume = _por_chave(await consultas.volume_por_intencao(banco_analitico, INICIO, FIM))

    assert volume["intencao_renomeada"] == 1


async def test_volume_ignora_mensagens_sem_intencao(banco_analitico, registrar):
    await registrar(criada_em=DENTRO, intencao_id=None, desfecho=Desfecho.BLOQUEADA_INJECAO_REGRA)

    volume = await consultas.volume_por_intencao(banco_analitico, INICIO, FIM)

    assert sum(linha.total for linha in volume) == 0


async def test_volume_ordena_do_maior_para_o_menor(banco_analitico, registrar):
    await registrar(criada_em=DENTRO, intencao_id="consultar_status_projeto")
    for _ in range(2):
        await registrar(criada_em=DENTRO, intencao_id="consultar_riscos_projeto")

    volume = await consultas.volume_por_intencao(banco_analitico, INICIO, FIM)

    assert [linha.chave for linha in volume[:2]] == [
        "consultar_riscos_projeto",
        "consultar_status_projeto",
    ]
    totais = [linha.total for linha in volume]
    assert totais == sorted(totais, reverse=True)


async def test_volume_filtra_pelo_perfil_da_interacao(banco_analitico, registrar):
    await registrar(criada_em=DENTRO, perfil=Perfil.DIRETORIA)
    await registrar(criada_em=DENTRO, perfil=Perfil.LIDER_PROJETO)
    await registrar(criada_em=DENTRO, perfil=Perfil.LIDER_PROJETO)

    volume = _por_chave(
        await consultas.volume_por_intencao(banco_analitico, INICIO, FIM, perfil=Perfil.DIRETORIA)
    )

    assert volume["consultar_status_projeto"] == 1


# --- Distribuição de desfechos ------------------------------------------------


async def test_desfechos_trazem_todos_os_valores_na_ordem_do_enum(banco_analitico, registrar):
    await registrar(criada_em=DENTRO, desfecho=Desfecho.BLOQUEADA_ABUSO)

    linhas = await consultas.distribuicao_de_desfechos(banco_analitico, INICIO, FIM)

    assert [linha.chave for linha in linhas] == [d.value for d in Desfecho]
    assert _por_chave(linhas) == {
        d.value: (1 if d is Desfecho.BLOQUEADA_ABUSO else 0) for d in Desfecho
    }


async def test_desfechos_contam_cada_valor_separadamente(banco_analitico, registrar):
    await registrar(criada_em=DENTRO, desfecho=Desfecho.ENCAMINHADA)
    await registrar(criada_em=DENTRO, desfecho=Desfecho.ENCAMINHADA)
    await registrar(criada_em=DENTRO, desfecho=Desfecho.BLOQUEADA_INJECAO_REGRA)
    await registrar(criada_em=DENTRO, desfecho=Desfecho.BLOQUEADA_INJECAO_MODELO)

    contagem = _por_chave(await consultas.distribuicao_de_desfechos(banco_analitico, INICIO, FIM))

    assert contagem[Desfecho.ENCAMINHADA.value] == 2
    assert contagem[Desfecho.BLOQUEADA_INJECAO_REGRA.value] == 1
    assert contagem[Desfecho.BLOQUEADA_INJECAO_MODELO.value] == 1


async def test_desfechos_filtram_pelo_perfil(banco_analitico, registrar):
    await registrar(criada_em=DENTRO, perfil=Perfil.MEMBRO_EQUIPE)
    await registrar(criada_em=DENTRO, perfil=Perfil.DIRETORIA)

    contagem = _por_chave(
        await consultas.distribuicao_de_desfechos(
            banco_analitico, INICIO, FIM, perfil=Perfil.MEMBRO_EQUIPE
        )
    )

    assert contagem[Desfecho.ENCAMINHADA.value] == 1


# --- Série de bloqueios -------------------------------------------------------


async def test_serie_traz_uma_linha_por_guarda(banco_analitico):
    serie = await consultas.serie_de_bloqueios(banco_analitico, INICIO, FIM)

    assert tuple(serie) == consultas.GUARDAS


async def test_serie_nao_soma_guardas_diferentes(banco_analitico, registrar):
    await registrar(criada_em=DENTRO, intencao_id=None, desfecho=Desfecho.BLOQUEADA_INJECAO_REGRA)
    await registrar(criada_em=DENTRO, intencao_id=None, desfecho=Desfecho.BLOQUEADA_ABUSO)
    await registrar(criada_em=DENTRO, desfecho=Desfecho.BLOQUEADA_SAIDA)

    serie = await consultas.serie_de_bloqueios(banco_analitico, INICIO, FIM)

    assert {guarda: sum(p.total for p in pontos) for guarda, pontos in serie.items()} == {
        "injecao": 1,
        "abuso": 1,
        "saida": 1,
    }
    assert "total" not in serie


async def test_serie_junta_as_duas_camadas_da_injecao(banco_analitico, registrar):
    await registrar(criada_em=DENTRO, intencao_id=None, desfecho=Desfecho.BLOQUEADA_INJECAO_REGRA)
    await registrar(criada_em=DENTRO, desfecho=Desfecho.BLOQUEADA_INJECAO_MODELO)

    serie = await consultas.serie_de_bloqueios(banco_analitico, INICIO, FIM)

    assert sum(ponto.total for ponto in serie["injecao"]) == 2


async def test_serie_ignora_desfechos_que_nao_sao_bloqueio(banco_analitico, registrar):
    await registrar(criada_em=DENTRO, desfecho=Desfecho.ENCAMINHADA)
    await registrar(criada_em=DENTRO, desfecho=Desfecho.RECUSADA_FORA_ESCOPO)
    await registrar(criada_em=DENTRO, desfecho=Desfecho.FALHA_EXECUTOR)

    serie = await consultas.serie_de_bloqueios(banco_analitico, INICIO, FIM)

    assert all(ponto.total == 0 for pontos in serie.values() for ponto in pontos)


async def test_serie_preenche_com_zero_os_dias_sem_evento(banco_analitico):
    serie = await consultas.serie_de_bloqueios(banco_analitico, INICIO, FIM)

    # Sete dias de janela terminando ao meio-dia tocam oito datas locais.
    assert len(serie["injecao"]) == 8
    momentos = [ponto.momento for ponto in serie["injecao"]]
    assert momentos == sorted(momentos)
    assert all(m.hour == 0 and m.minute == 0 for m in momentos)


async def test_serie_agrupa_no_fuso_de_sao_paulo(banco_analitico, registrar):
    # 01h UTC de 21/09 ainda é 22h de 20/09 em São Paulo.
    await registrar(
        criada_em=datetime(2026, 9, 21, 1, 0, tzinfo=UTC),
        intencao_id=None,
        desfecho=Desfecho.BLOQUEADA_ABUSO,
    )

    serie = await consultas.serie_de_bloqueios(banco_analitico, INICIO, FIM)

    com_evento = [p for p in serie["abuso"] if p.total]
    assert len(com_evento) == 1
    assert com_evento[0].momento.date().isoformat() == "2026-09-20"
    assert com_evento[0].momento.utcoffset() == timedelta(hours=-3)


async def test_serie_por_hora(banco_analitico, registrar):
    inicio = FIM - timedelta(hours=6)
    await registrar(
        criada_em=FIM - timedelta(minutes=90),
        intencao_id=None,
        desfecho=Desfecho.BLOQUEADA_INJECAO_REGRA,
    )

    serie = await consultas.serie_de_bloqueios(banco_analitico, inicio, FIM, granularidade="hora")

    assert len(serie["injecao"]) == 6
    assert sum(ponto.total for ponto in serie["injecao"]) == 1


async def test_serie_recusa_granularidade_desconhecida(banco_analitico):
    with pytest.raises(ValueError, match="Granularidade"):
        await consultas.serie_de_bloqueios(banco_analitico, INICIO, FIM, granularidade="semana")


# --- Enunciados agrupados -----------------------------------------------------


async def test_fora_de_escopo_agrupa_pedidos_repetidos(banco_analitico, registrar):
    for prompt in ("Qual o saldo do contrato?", "qual o saldo do contrato? ", "Abrir chamado"):
        await registrar(
            criada_em=DENTRO,
            intencao_id=catalogo.FORA_DE_ESCOPO,
            desfecho=Desfecho.RECUSADA_FORA_ESCOPO,
            prompt=prompt,
            confianca=0.3,
        )

    enunciados = await consultas.enunciados_fora_de_escopo(banco_analitico, INICIO, FIM)

    assert [e.ocorrencias for e in enunciados] == [2, 1]
    assert enunciados[0].prompt.lower() == "qual o saldo do contrato?"
    assert enunciados[0].confianca_media == pytest.approx(0.3)


async def test_fora_de_escopo_inclui_recusas_sem_rotulo(banco_analitico, registrar):
    await registrar(
        criada_em=DENTRO,
        intencao_id=None,
        desfecho=Desfecho.RECUSADA_FORA_ESCOPO,
        prompt="Qual a previsão do tempo?",
    )

    enunciados = await consultas.enunciados_fora_de_escopo(banco_analitico, INICIO, FIM)

    assert [e.prompt for e in enunciados] == ["Qual a previsão do tempo?"]


async def test_fora_de_escopo_nao_mistura_outros_desfechos(banco_analitico, registrar):
    await registrar(criada_em=DENTRO, desfecho=Desfecho.RECUSADA_BAIXA_CONFIANCA)
    await registrar(criada_em=DENTRO, desfecho=Desfecho.ENCAMINHADA)

    assert await consultas.enunciados_fora_de_escopo(banco_analitico, INICIO, FIM) == []


async def test_enunciados_desempatam_pelo_mais_recente(banco_analitico, registrar):
    await registrar(
        criada_em=DENTRO - timedelta(days=2),
        desfecho=Desfecho.RECUSADA_BAIXA_CONFIANCA,
        prompt="Como está tudo por lá?",
    )
    await registrar(
        criada_em=DENTRO,
        desfecho=Desfecho.RECUSADA_BAIXA_CONFIANCA,
        prompt="E o andamento daquele projeto?",
    )

    enunciados = await consultas.enunciados_baixa_confianca(banco_analitico, INICIO, FIM)

    assert enunciados[0].prompt == "E o andamento daquele projeto?"
    assert enunciados[0].ultima_em == DENTRO
    assert enunciados[0].ultima_em.tzinfo is not None


async def test_baixa_confianca_calcula_a_media_do_grupo(banco_analitico, registrar):
    for confianca in (0.4, 0.5):
        await registrar(
            criada_em=DENTRO,
            desfecho=Desfecho.RECUSADA_BAIXA_CONFIANCA,
            prompt="Como está tudo por lá?",
            confianca=confianca,
        )

    [enunciado] = await consultas.enunciados_baixa_confianca(banco_analitico, INICIO, FIM)

    assert enunciado.ocorrencias == 2
    assert enunciado.confianca_media == pytest.approx(0.45)


async def test_enunciados_respeitam_o_limite(banco_analitico, registrar):
    for indice in range(5):
        await registrar(
            criada_em=DENTRO,
            desfecho=Desfecho.RECUSADA_FORA_ESCOPO,
            prompt=f"Pedido número {indice}",
        )

    enunciados = await consultas.enunciados_fora_de_escopo(banco_analitico, INICIO, FIM, limite=3)

    assert len(enunciados) == 3


async def test_enunciados_recusam_limite_nao_positivo(banco_analitico):
    with pytest.raises(ValueError, match="Limite"):
        await consultas.enunciados_baixa_confianca(banco_analitico, INICIO, FIM, limite=0)
