"""Casos TF-RF08-01 a TF-RF08-04 — relatórios gerenciais."""

import pytest

from app.pipeline.desfechos import Desfecho
from app.pipeline.orquestrador import Orquestrador
from app.schemas.chat import ChatRequest
from app.schemas.usuario import Perfil, UsuarioAutenticado


@pytest.mark.parametrize(
    "intencao_id",
    ("gerar_relatorio_status", "gerar_previa_diretoria", "gerar_relatorio_encerramento"),
)
async def test_tf_rf08_01_tipo_de_material_chega_ao_executor(
    intencao_id, pipeline_controlado, executor_espiao, repositorio_memoria
) -> None:
    pipeline_controlado(intencao_id, 0.99)
    pipeline = Orquestrador(executor_espiao, repositorio_memoria, repositorio_memoria)
    usuario = UsuarioAutenticado("rf08", "Teste RF08", Perfil.DIRETORIA)
    resposta = await pipeline.processar(ChatRequest(mensagem="Gere o material"), usuario)
    assert resposta.desfecho == Desfecho.ENCAMINHADA.value
    assert executor_espiao.chamadas == [("Gere o material", intencao_id)]


@pytest.mark.xfail(strict=True, reason="perfil ainda não é enviado ao contrato do executor")
async def test_tf_rf08_02_detalhe_do_material_varia_por_perfil(
    pipeline_controlado, executor_espiao, repositorio_memoria
) -> None:
    pipeline_controlado("gerar_relatorio_status", 0.99)
    pipeline = Orquestrador(executor_espiao, repositorio_memoria, repositorio_memoria)
    respostas = []
    for perfil in (Perfil.DIRETORIA, Perfil.MEMBRO_EQUIPE):
        resposta = await pipeline.processar(
            ChatRequest(mensagem="Gere o relatório"),
            UsuarioAutenticado(perfil.value, perfil.value, perfil),
        )
        respostas.append(resposta.resposta)
    assert respostas[0] != respostas[1]


@pytest.mark.xfail(strict=True, reason="regra de suficiência de dados do relatório ainda não implementada")
async def test_tf_rf08_03_dados_insuficientes_nao_geram_material(
    pipeline_controlado, executor_espiao, repositorio_memoria
) -> None:
    pipeline_controlado("gerar_relatorio_status", 0.99)
    pipeline = Orquestrador(executor_espiao, repositorio_memoria, repositorio_memoria)
    resposta = await pipeline.processar(
        ChatRequest(mensagem="Gere relatório do projeto sem dados"),
        UsuarioAutenticado("rf08", "Teste", Perfil.DIRETORIA),
    )
    assert resposta.desfecho != Desfecho.ENCAMINHADA.value


@pytest.mark.xfail(strict=True, reason="filtragem de fontes por projeto ainda não integra o executor")
async def test_tf_rf08_04_material_nao_recebe_fonte_nao_autorizada(
    pipeline_controlado, executor_espiao, repositorio_memoria
) -> None:
    pipeline_controlado("gerar_relatorio_status", 0.99)
    pipeline = Orquestrador(executor_espiao, repositorio_memoria, repositorio_memoria)
    usuario = UsuarioAutenticado("rf08", "Teste", Perfil.DIRETORIA, projetos=frozenset())
    await pipeline.processar(ChatRequest(mensagem="Relatório do PRJ-SECRETO"), usuario)
    assert executor_espiao.chamadas == []
