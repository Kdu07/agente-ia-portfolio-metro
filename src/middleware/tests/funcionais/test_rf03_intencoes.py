"""Casos TF-RF03-01 a TF-RF03-08 — identificação e controle de intenções."""

import pytest

from app.pipeline import orquestrador as orq
from app.pipeline.desfechos import Desfecho
from app.pipeline.intencao import catalogo, classificador
from app.pipeline.intencao.classificador import ResultadoIntencao
from app.pipeline.orquestrador import Orquestrador
from app.schemas.chat import ChatRequest
from app.schemas.usuario import Perfil, UsuarioAutenticado

USUARIO = UsuarioAutenticado("rf03", "Teste RF03", Perfil.LIDER_PROJETO)


def test_tf_rf03_01_enunciado_canonico_classifica_na_intencao_correta() -> None:
    intencoes = [
        item
        for item in catalogo.CATALOGO.values()
        if item.status_treino is catalogo.StatusTreino.TREINADO_MVP and item.exemplos
    ]
    artefato = classificador.obter_artefato()
    probabilidades = artefato.pipeline.predict_proba([item.exemplos[0] for item in intencoes])

    for intencao, distribuicao in zip(intencoes, probabilidades, strict=True):
        indice = int(distribuicao.argmax())
        prevista = str(artefato.pipeline.classes_[indice])
        confianca = float(distribuicao[indice])
        limiar = artefato.limiares.get(intencao.id, intencao.limiar_confianca)
        assert prevista == intencao.id
        assert confianca >= limiar


async def test_tf_rf03_02_intencao_resolvida_chega_ao_executor(
    pipeline_controlado, executor_espiao, repositorio_memoria
) -> None:
    pipeline = Orquestrador(executor_espiao, repositorio_memoria, repositorio_memoria)
    resposta = await pipeline.processar(ChatRequest(mensagem="Status do projeto A"), USUARIO)
    assert resposta.desfecho == Desfecho.ENCAMINHADA.value
    assert executor_espiao.chamadas == [("Status do projeto A", "consultar_status_projeto")]


async def test_tf_rf03_03_fora_de_escopo_produz_recusa_orientativa(
    pipeline_controlado, executor_espiao, repositorio_memoria
) -> None:
    pipeline_controlado(catalogo.FORA_DE_ESCOPO, 0.99)
    pipeline = Orquestrador(executor_espiao, repositorio_memoria, repositorio_memoria)
    resposta = await pipeline.processar(ChatRequest(mensagem="Conte uma piada"), USUARIO)
    assert resposta.desfecho == Desfecho.RECUSADA_FORA_ESCOPO.value
    assert "portfólio" in resposta.resposta
    assert executor_espiao.chamadas == []


async def test_tf_rf03_04_baixa_confianca_pede_reformulacao(
    pipeline_controlado, executor_espiao, repositorio_memoria
) -> None:
    pipeline_controlado("consultar_status_projeto", 0.01)
    pipeline = Orquestrador(executor_espiao, repositorio_memoria, repositorio_memoria)
    resposta = await pipeline.processar(ChatRequest(mensagem="E aquele negócio?"), USUARIO)
    assert resposta.desfecho == Desfecho.RECUSADA_BAIXA_CONFIANCA.value
    assert executor_espiao.chamadas == []


@pytest.mark.xfail(strict=True, reason="pipeline não distingue recusa por projeto")
async def test_tf_rf03_05_recusa_por_permissao_difere_de_fora_de_escopo(
    pipeline_controlado, executor_espiao, repositorio_memoria
) -> None:
    pipeline = Orquestrador(executor_espiao, repositorio_memoria, repositorio_memoria)
    sem_projeto = UsuarioAutenticado("sem-acesso", "Sem acesso", Perfil.MEMBRO_EQUIPE)
    resposta = await pipeline.processar(
        ChatRequest(mensagem="Status do projeto PRJ-RESTRITO"), sem_projeto
    )
    assert resposta.desfecho not in {
        Desfecho.ENCAMINHADA.value,
        Desfecho.RECUSADA_FORA_ESCOPO.value,
    }


@pytest.mark.xfail(strict=True, reason="validação de entidades ainda não implementada")
async def test_tf_rf03_06_entidade_obrigatoria_ausente_pede_complemento(
    pipeline_controlado, executor_espiao, repositorio_memoria
) -> None:
    pipeline = Orquestrador(executor_espiao, repositorio_memoria, repositorio_memoria)
    resposta = await pipeline.processar(ChatRequest(mensagem="Qual é o status?"), USUARIO)
    assert resposta.desfecho != Desfecho.ENCAMINHADA.value
    assert executor_espiao.chamadas == []


async def test_tf_rf03_07_solicitacao_recusada_fica_registrada(
    pipeline_controlado, executor_espiao, repositorio_memoria
) -> None:
    pipeline_controlado(catalogo.FORA_DE_ESCOPO, 0.99)
    pipeline = Orquestrador(executor_espiao, repositorio_memoria, repositorio_memoria)
    resposta = await pipeline.processar(ChatRequest(mensagem="Previsão do tempo"), USUARIO)
    assert len(repositorio_memoria.interacoes) == 1
    assert repositorio_memoria.interacoes[0].id == resposta.interacao_id
    assert repositorio_memoria.interacoes[0].desfecho is Desfecho.RECUSADA_FORA_ESCOPO


async def test_tf_rf03_08_classe_de_manipulacao_produz_bloqueio_seco(
    pipeline_controlado, executor_espiao, repositorio_memoria, monkeypatch
) -> None:
    async def tentativa(_: str) -> ResultadoIntencao:
        return ResultadoIntencao(catalogo.TENTATIVA_INJECAO, 0.99)

    monkeypatch.setattr(orq.intencao_classificador, "classificar", tentativa)
    pipeline = Orquestrador(executor_espiao, repositorio_memoria, repositorio_memoria)
    resposta = await pipeline.processar(ChatRequest(mensagem="texto adversarial"), USUARIO)
    assert resposta.desfecho == Desfecho.BLOQUEADA_INJECAO_MODELO.value
    assert resposta.bloqueada
    assert executor_espiao.chamadas == []
