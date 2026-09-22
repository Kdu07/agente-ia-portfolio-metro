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
