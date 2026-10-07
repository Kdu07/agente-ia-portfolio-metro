"""Casos TF-RF10-01 a TF-RF10-05 — registro e recortes de intenções."""

from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app.analytics.consultas import ContagemPorChave, EnunciadoAgrupado, PontoSerie
from app.api import deps
from app.api.routes import intencoes as rotas_intencoes
from app.executor.base import RespostaExecutor
from app.main import app
from app.pipeline import orquestrador as orq
from app.pipeline.desfechos import Desfecho
from app.pipeline.guardas.abuso.classificador import ResultadoAbuso
from app.pipeline.guardas.injecao.classificador import ResultadoInjection
from app.pipeline.guardas.saida import ResultadoSaida
from app.pipeline.intencao import catalogo
from app.pipeline.intencao.classificador import ResultadoIntencao
from app.pipeline.orquestrador import Orquestrador
from app.schemas.chat import ChatRequest
from app.schemas.usuario import Perfil, Permissao, UsuarioAutenticado

USUARIO = UsuarioAutenticado("rf10", "Teste RF10", Perfil.LIDER_PROJETO)


async def _produzir_todos_os_desfechos(monkeypatch, repositorio_memoria) -> None:
    estado = {"modo": "encaminhada"}

    def regra(_: str) -> bool:
        return estado["modo"] == "injecao_regra"

    async def injecao(_: str) -> ResultadoInjection:
        if estado["modo"] == "falha_guarda":
            return ResultadoInjection(True, 1.0, "servico_indisponivel", indisponivel=True)
        return ResultadoInjection(estado["modo"] == "injecao_modelo", 0.99, "teste")

    async def abuso(_: str) -> ResultadoAbuso:
        return ResultadoAbuso(estado["modo"] == "abuso", 0.99)

    async def intencao(_: str) -> ResultadoIntencao:
        if estado["modo"] == "fora_escopo":
            return ResultadoIntencao(catalogo.FORA_DE_ESCOPO, 0.99)
        confianca = 0.01 if estado["modo"] == "baixa_confianca" else 0.99
        return ResultadoIntencao("consultar_status_projeto", confianca)

    async def saida(_: str, __: str) -> ResultadoSaida:
        return ResultadoSaida(estado["modo"] == "saida", 0.99, "teste")

    class Executor:
        async def enviar(self, *args, **kwargs) -> RespostaExecutor:
            if estado["modo"] == "falha_executor":
                raise RuntimeError("falha controlada")
            return RespostaExecutor(texto="resposta")

    monkeypatch.setattr(orq.injecao_regras, "contem_padrao_suspeito", regra)
    monkeypatch.setattr(orq.injecao_classificador, "classificar", injecao)
    monkeypatch.setattr(orq.abuso_classificador, "classificar", abuso)
    monkeypatch.setattr(orq.intencao_classificador, "classificar", intencao)
    monkeypatch.setattr(orq.intencao_classificador, "limiar_de", lambda _: None)
    monkeypatch.setattr(orq.guarda_saida, "verificar", saida)
    pipeline = Orquestrador(Executor(), repositorio_memoria, repositorio_memoria)

    for modo in (
        "encaminhada",
        "injecao_regra",
        "injecao_modelo",
        "abuso",
        "fora_escopo",
        "baixa_confianca",
        "saida",
        "falha_guarda",
        "falha_executor",
    ):
        estado["modo"] = modo
        await pipeline.processar(ChatRequest(mensagem=f"caso {modo}"), USUARIO)


async def test_tf_rf10_01_uma_linha_por_solicitacao_sem_duplicidade(
    monkeypatch, repositorio_memoria
) -> None:
    await _produzir_todos_os_desfechos(monkeypatch, repositorio_memoria)
    registros = repositorio_memoria.interacoes
    assert len(registros) == len(Desfecho) == 9
    assert len({registro.id for registro in registros}) == 9
    assert {registro.desfecho for registro in registros} == set(Desfecho)


async def test_tf_rf10_02_registro_contem_os_cinco_campos_obrigatorios(
    monkeypatch, repositorio_memoria
) -> None:
    await _produzir_todos_os_desfechos(monkeypatch, repositorio_memoria)
    for registro in repositorio_memoria.interacoes:
        assert hasattr(registro, "intencao_id")
        assert hasattr(registro, "confianca_intencao")
        assert registro.perfil == Perfil.LIDER_PROJETO.value
        assert registro.canal.value == "chat"
        assert isinstance(registro.desfecho, Desfecho)


def _usuario_sem_intencoes() -> UsuarioAutenticado:
    return UsuarioAutenticado(
        "sem-permissao",
        "Sem permissão",
        Perfil.DIRETORIA,
        permissoes=frozenset({Permissao.GERIR_ROTINAS}),
    )


def test_tf_rf10_03_perfil_sem_permissao_nao_acessa_recortes() -> None:
    app.dependency_overrides[deps.obter_usuario_atual] = _usuario_sem_intencoes
    try:
        with TestClient(app) as cliente:
            resposta = cliente.get("/intencoes/volume")
        assert resposta.status_code == 403
        assert "ver_intencoes" in resposta.json()["detail"]
    finally:
        app.dependency_overrides.clear()


def test_tf_rf10_04_acesso_direto_tambem_e_negado_no_servidor() -> None:
    app.dependency_overrides[deps.obter_usuario_atual] = _usuario_sem_intencoes
    try:
        with TestClient(app) as cliente:
            respostas = [
                cliente.get("/intencoes/desfechos"),
                cliente.get("/intencoes/seguranca/serie"),
                cliente.get("/intencoes/catalogo/fora-de-escopo"),
            ]
        assert {resposta.status_code for resposta in respostas} == {403}
    finally:
        app.dependency_overrides.clear()


async def test_tf_rf10_05_recortes_analiticos_previstos_sao_produzidos(monkeypatch) -> None:
    agora = datetime.now(UTC)

    async def volume(*args, **kwargs):
        return [ContagemPorChave("consultar_riscos", 2)]

    async def desfechos(*args, **kwargs):
        return [ContagemPorChave(Desfecho.ENCAMINHADA.value, 2)]

    async def serie(*args, **kwargs):
        return {"injecao": [PontoSerie(agora, 1)], "abuso": [], "saida": []}

    async def fora(*args, **kwargs):
        return [EnunciadoAgrupado("pergunta desconhecida", 1, agora, 0.2)]

    monkeypatch.setattr(rotas_intencoes.consultas, "volume_por_intencao", volume)
    monkeypatch.setattr(rotas_intencoes.consultas, "distribuicao_de_desfechos", desfechos)
    monkeypatch.setattr(rotas_intencoes.consultas, "serie_de_bloqueios", serie)
    monkeypatch.setattr(rotas_intencoes.consultas, "enunciados_fora_de_escopo", fora)

    assert (await rotas_intencoes.volume_por_intencao(object()))[0].total == 2
    assert (await rotas_intencoes.distribuicao_de_desfechos(object()))[0].chave == "encaminhada"
    assert (await rotas_intencoes.serie_de_bloqueios(object()))[0].nome == "injecao"
    assert (await rotas_intencoes.enunciados_fora_de_escopo(object()))[0].ocorrencias == 1
