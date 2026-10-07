"""Integração HTTP das sete rotas de rotinas."""

from dataclasses import replace
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from app.api import deps
from app.api.routes import rotinas as rotas_rotinas
from app.main import app
from app.persistence.models import (
    Canal,
    ExecucaoRotina,
    Interacao,
    Rotina,
    StatusExecucao,
)
from app.pipeline.desfechos import Desfecho
from app.rotinas.validacao import ResultadoValidacao
from app.schemas.chat import ChatResponse
from app.schemas.usuario import Perfil, Permissao, UsuarioAutenticado

AGORA = datetime.now(UTC)
USUARIO = UsuarioAutenticado(
    id="usuario-a",
    nome="Usuário A",
    perfil=Perfil.LIDER_PROJETO,
    permissoes=frozenset({Permissao.GERIR_ROTINAS}),
)


def _rotina(rotina_id: str, dono_id: str = USUARIO.id, *, ativa: bool = True) -> Rotina:
    return Rotina(
        id=rotina_id,
        nome=f"Rotina {rotina_id}",
        prompt="Liste os riscos críticos do projeto",
        agenda_cron="0 8 * * 1",
        timezone="America/Sao_Paulo",
        dono_id=dono_id,
        ativa=ativa,
        criada_em=AGORA,
        atualizada_em=AGORA,
        intencao_prevista="consultar_riscos",
    )


class RotinasMemoria:
    def __init__(self) -> None:
        self.itens = {
            "rotina-a": _rotina("rotina-a"),
            "rotina-inativa": _rotina("rotina-inativa", ativa=False),
            "rotina-b": _rotina("rotina-b", "usuario-b"),
        }
        self.com_historico: set[str] = set()

    async def listar_por_dono(self, dono_id: str) -> list[Rotina]:
        return [item for item in self.itens.values() if item.dono_id == dono_id]

    async def obter(self, rotina_id: str) -> Rotina | None:
        return self.itens.get(rotina_id)

    async def criar(self, rotina: Rotina) -> None:
        self.itens[rotina.id] = rotina

    async def atualizar(self, rotina: Rotina) -> None:
        self.itens[rotina.id] = rotina

    async def remover(self, rotina_id: str) -> None:
        if rotina_id in self.com_historico:
            raise ValueError("Desative-a em vez de removê-la.")
        self.itens.pop(rotina_id, None)


class ExecucoesMemoria:
    def __init__(self) -> None:
        self.registros: dict[str, tuple[ExecucaoRotina, Interacao | None]] = {}

    async def obter_com_interacao(self, execucao_id: str):
        return self.registros.get(execucao_id)

    async def listar_com_interacao_por_rotina(self, rotina_id: str, *, limite: int = 20):
        return [
            registro for registro in self.registros.values() if registro[0].rotina_id == rotina_id
        ][:limite]

    async def ultimas_por_rotina(self, rotina_ids: list[str]) -> dict[str, ExecucaoRotina]:
        ultimas: dict[str, ExecucaoRotina] = {}
        for execucao, _ in self.registros.values():
            atual = ultimas.get(execucao.rotina_id)
            if execucao.rotina_id in rotina_ids and (
                atual is None or execucao.iniciada_em > atual.iniciada_em
            ):
                ultimas[execucao.rotina_id] = execucao
        return ultimas


def _registrar_execucao(repositorio: ExecucoesMemoria, rotina_id: str = "rotina-a") -> None:
    interacao = Interacao(
        id="int-1",
        conversa_id="conv-1",
        usuario_id=USUARIO.id,
        perfil=USUARIO.perfil.value,
        canal=Canal.ROTINA,
        prompt="Liste os riscos críticos do projeto",
        resposta="Foram encontrados dois riscos críticos.",
        intencao_id="consultar_riscos",
        confianca_intencao=0.95,
        desfecho=Desfecho.ENCAMINHADA,
        latencia_ms=120,
        criada_em=AGORA,
        rotina_id=rotina_id,
    )
    execucao = ExecucaoRotina(
        id="exec-1",
        rotina_id=rotina_id,
        iniciada_em=AGORA,
        concluida_em=AGORA,
        status=StatusExecucao.SUCESSO,
        interacao_id=interacao.id,
    )
    repositorio.registros[execucao.id] = execucao, interacao


@pytest.fixture
def api_rotinas(monkeypatch: pytest.MonkeyPatch):
    rotinas = RotinasMemoria()
    execucoes = ExecucoesMemoria()

    async def validar_prompt(prompt: str) -> ResultadoValidacao:
        if prompt == "prompt inválido":
            return ResultadoValidacao(False, erro="Prompt não reconhecido.")
        return ResultadoValidacao(True, intencao_prevista="consultar_riscos")

    monkeypatch.setattr(rotas_rotinas, "validar_prompt", validar_prompt)
    app.dependency_overrides[deps.obter_usuario_atual] = lambda: USUARIO
    app.dependency_overrides[deps.obter_rotinas] = lambda: rotinas
    app.dependency_overrides[deps.obter_execucoes] = lambda: execucoes
    with TestClient(app) as client:
        yield client, rotinas, execucoes
    app.dependency_overrides.clear()


def _pedido(**alteracoes) -> dict:
    dados = {
        "nome": "Riscos semanais",
        "prompt": "Liste os riscos críticos do projeto",
        "agenda_cron": "0 8 * * 1",
        "timezone": "America/Sao_Paulo",
        "ativa": True,
    }
    dados.update(alteracoes)
    return dados


def test_lista_somente_rotinas_do_usuario_e_calcula_proximo_disparo(api_rotinas) -> None:
    client, _, _ = api_rotinas
    resposta = client.get("/rotinas")

    assert resposta.status_code == 200
    itens = {item["id"]: item for item in resposta.json()}
    assert set(itens) == {"rotina-a", "rotina-inativa"}
    assert itens["rotina-a"]["proximo_disparo"] is not None
    assert itens["rotina-inativa"]["proximo_disparo"] is None


def test_devolve_o_rotulo_legivel_da_intencao_prevista(api_rotinas) -> None:
    """A tela de rotinas mostra o rótulo do catálogo, e não o id técnico.

    Uma intenção sem rótulo cadastrado recebe um nome derivado do id, como
    no painel de intenções, em vez de aparecer crua.
    """
    client, rotinas, _ = api_rotinas
    rotinas.itens["rotina-a"] = replace(
        rotinas.itens["rotina-a"],
        intencao_prevista="intencao_sem_rotulo",
    )

    itens = {item["id"]: item for item in client.get("/rotinas").json()}

    assert itens["rotina-inativa"]["intencao_prevista"] == "consultar_riscos"
    assert itens["rotina-inativa"]["intencao_prevista_rotulo"] == "Consultar riscos"
    assert itens["rotina-a"]["intencao_prevista_rotulo"] == "Intencao sem rotulo"


def test_lista_o_ultimo_disparo_de_cada_rotina(api_rotinas) -> None:
    """A lista diz como foi o último disparo sem abrir o histórico.

    A rotina que nunca disparou vem com `ultima_execucao` nula, e não com
    um disparo inventado.
    """
    client, _, execucoes = api_rotinas
    _registrar_execucao(execucoes)

    itens = {item["id"]: item for item in client.get("/rotinas").json()}

    assert itens["rotina-a"]["ultima_execucao"]["status"] == "sucesso"
    assert itens["rotina-a"]["ultima_execucao"]["iniciada_em"].startswith(AGORA.date().isoformat())
    assert itens["rotina-inativa"]["ultima_execucao"] is None


def test_edicao_preserva_o_ultimo_disparo_na_resposta(api_rotinas) -> None:
    client, _, execucoes = api_rotinas
    _registrar_execucao(execucoes)

    resposta = client.put("/rotinas/rotina-a", json=_pedido(nome="Novo nome"))

    assert resposta.json()["ultima_execucao"]["status"] == "sucesso"


def test_valida_prompt_e_agenda_sem_persistir(api_rotinas) -> None:
    client, rotinas, _ = api_rotinas
    quantidade = len(rotinas.itens)

    assert client.post("/rotinas/validar", json=_pedido()).json() == {
        "valida": True,
        "intencao_prevista": "consultar_riscos",
        "erro": None,
    }
    invalida = client.post(
        "/rotinas/validar",
        json=_pedido(agenda_cron="cron inválido"),
    )
    assert invalida.status_code == 200
    assert invalida.json()["valida"] is False
    assert len(rotinas.itens) == quantidade


def test_cria_rotina_com_dono_e_intencao_resolvidos_no_servidor(api_rotinas) -> None:
    client, rotinas, _ = api_rotinas
    resposta = client.post("/rotinas", json=_pedido())

    assert resposta.status_code == 201
    criada = rotinas.itens[resposta.json()["id"]]
    assert criada.dono_id == USUARIO.id
    assert criada.intencao_prevista == "consultar_riscos"
    assert resposta.json()["proximo_disparo"] is not None


@pytest.mark.parametrize(
    ("dia_semana", "dia_esperado"),
    [("0", 11), ("1", 5), ("1-5", 5), ("7", 11), ("mon-fri", 5)],
)
def test_api_valida_cria_edita_e_lista_com_dias_do_cron_padrao(
    api_rotinas, monkeypatch, dia_semana, dia_esperado
) -> None:
    client, rotinas, _ = api_rotinas

    class RelogioFixo(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 10, 4, 12, tzinfo=UTC).astimezone(tz)

    monkeypatch.setattr(rotas_rotinas, "datetime", RelogioFixo)
    pedido = _pedido(agenda_cron=f"0 8 * * {dia_semana}")
    quantidade = len(rotinas.itens)
    validada = client.post("/rotinas/validar", json=pedido)
    assert validada.status_code == 200
    assert validada.json()["valida"] is True
    assert len(rotinas.itens) == quantidade

    criada = client.post("/rotinas", json=pedido)
    assert criada.status_code == 201
    rotina_id = criada.json()["id"]
    atualizada = client.put(f"/rotinas/{rotina_id}", json=pedido)
    assert atualizada.status_code == 200
    listada = next(item for item in client.get("/rotinas").json() if item["id"] == rotina_id)
    for resposta in (criada.json(), atualizada.json(), listada):
        assert resposta["agenda_cron"] == pedido["agenda_cron"]
        assert datetime.fromisoformat(resposta["proximo_disparo"]) == datetime.fromisoformat(
            f"2026-10-{dia_esperado:02d}T08:00:00-03:00"
        )


@pytest.mark.parametrize("dia_semana", ["8", "-1", "5-1", "1-8", "*/0", "1-5/0"])
def test_api_recusa_dia_da_semana_invalido_sem_gravar(api_rotinas, dia_semana) -> None:
    client, rotinas, _ = api_rotinas
    pedido = _pedido(agenda_cron=f"0 8 * * {dia_semana}")
    anteriores = dict(rotinas.itens)
    validada = client.post("/rotinas/validar", json=pedido)
    assert validada.status_code == 200
    assert validada.json()["valida"] is False
    assert "dia da semana" in validada.json()["erro"]
    for resposta in (
        client.post("/rotinas", json=pedido),
        client.put("/rotinas/rotina-a", json=pedido),
    ):
        assert resposta.status_code == 422
        assert "dia da semana" in resposta.json()["detail"]
    assert rotinas.itens == anteriores


def test_criacao_invalida_retorna_422_e_nao_grava(api_rotinas) -> None:
    client, rotinas, _ = api_rotinas
    quantidade = len(rotinas.itens)
    resposta = client.post("/rotinas", json=_pedido(prompt="prompt inválido"))

    assert resposta.status_code == 422
    assert resposta.json()["detail"] == "Prompt não reconhecido."
    assert len(rotinas.itens) == quantidade


def test_atualiza_apenas_rotina_do_proprio_usuario_e_revalida(api_rotinas) -> None:
    client, rotinas, _ = api_rotinas
    resposta = client.put("/rotinas/rotina-a", json=_pedido(nome="Novo nome"))

    assert resposta.status_code == 200
    assert rotinas.itens["rotina-a"].nome == "Novo nome"
    assert client.put("/rotinas/rotina-b", json=_pedido()).status_code == 404
    assert (
        client.put(
            "/rotinas/rotina-a",
            json=_pedido(prompt="prompt inválido"),
        ).status_code
        == 422
    )


def test_remove_rotina_propria_sem_historico_e_preserva_as_demais(api_rotinas) -> None:
    client, rotinas, _ = api_rotinas

    assert client.delete("/rotinas/rotina-a").status_code == 204
    assert "rotina-a" not in rotinas.itens
    assert client.delete("/rotinas/rotina-b").status_code == 404
    assert "rotina-b" in rotinas.itens


def test_rotina_com_historico_deve_ser_desativada_em_vez_de_excluida(api_rotinas) -> None:
    client, rotinas, _ = api_rotinas
    rotinas.com_historico.add("rotina-a")

    resposta = client.delete("/rotinas/rotina-a")

    assert resposta.status_code == 409
    assert "Desative-a" in resposta.json()["detail"]


def test_execucao_manual_devolve_o_registro_persistido(
    api_rotinas,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _, execucoes = api_rotinas
    _registrar_execucao(execucoes)

    async def executar(rotina_id: str, solicitante_id: str) -> ChatResponse:
        assert (rotina_id, solicitante_id) == ("rotina-a", USUARIO.id)
        return ChatResponse(
            resposta="Foram encontrados dois riscos críticos.",
            conversa_id="conv-1",
            desfecho=Desfecho.ENCAMINHADA.value,
            interacao_id="int-1",
            execucao_id="exec-1",
        )

    monkeypatch.setattr(rotas_rotinas.execucao_rotina, "executar_agora", executar)
    resposta = client.post("/rotinas/rotina-a/executar")

    assert resposta.status_code == 200
    assert resposta.json()["id"] == "exec-1"
    assert resposta.json()["resposta"] == "Foram encontrados dois riscos críticos."
    assert resposta.json()["desfecho"] == "encaminhada"


def test_historico_exibe_resultado_e_nao_vaza_rotina_alheia(api_rotinas) -> None:
    client, _, execucoes = api_rotinas
    _registrar_execucao(execucoes)

    resposta = client.get("/rotinas/rotina-a/execucoes")

    assert resposta.status_code == 200
    assert resposta.json()[0]["status"] == "sucesso"
    assert resposta.json()[0]["resposta"] == "Foram encontrados dois riscos críticos."
    assert client.get("/rotinas/rotina-b/execucoes").status_code == 404
    assert client.get("/rotinas/rotina-a/execucoes?limite=0").status_code == 422


def test_todas_as_rotas_exigem_permissao_de_gerir_rotinas() -> None:
    sem_permissao = replace(USUARIO, permissoes=frozenset())
    app.dependency_overrides[deps.obter_usuario_atual] = lambda: sem_permissao
    try:
        with TestClient(app) as client:
            assert client.get("/rotinas").status_code == 403
            assert client.post("/rotinas/validar", json=_pedido()).status_code == 403
            assert client.post("/rotinas", json=_pedido()).status_code == 403
            assert client.put("/rotinas/rotina-a", json=_pedido()).status_code == 403
            assert client.delete("/rotinas/rotina-a").status_code == 403
            assert client.post("/rotinas/rotina-a/executar").status_code == 403
            assert client.get("/rotinas/rotina-a/execucoes").status_code == 403
    finally:
        app.dependency_overrides.clear()
