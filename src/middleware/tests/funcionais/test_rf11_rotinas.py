"""Casos TF-RF11-01 a TF-RF11-06 — cadastro e execução de rotinas."""

from datetime import UTC, datetime

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.api import deps
from app.api.routes import rotinas as rotas
from app.main import app
from app.persistence.models import Rotina, StatusExecucao
from app.pipeline.desfechos import Desfecho
from app.rotinas import agendador, execucao
from app.rotinas.validacao import ResultadoValidacao
from app.schemas.chat import ChatResponse
from app.schemas.rotina import RotinaRequest
from app.schemas.usuario import Perfil, Permissao, UsuarioAutenticado

AGORA = datetime.now(UTC)
USUARIO = UsuarioAutenticado(
    "rf11",
    "Teste RF11",
    Perfil.LIDER_PROJETO,
    permissoes=frozenset({Permissao.GERIR_ROTINAS}),
)


def _rotina() -> Rotina:
    return Rotina(
        "rotina-rf11",
        "Riscos semanais",
        "Liste os riscos críticos",
        "0 8 * * 1-5",
        "America/Sao_Paulo",
        USUARIO.id,
        True,
        AGORA,
        AGORA,
        "consultar_riscos",
    )


class RotinasMemoria:
    def __init__(self) -> None:
        self.itens: dict[str, Rotina] = {}

    async def criar(self, rotina: Rotina) -> None:
        self.itens[rotina.id] = rotina


async def test_tf_rf11_01_cadastro_persiste_agenda_fuso_e_registra_job(monkeypatch) -> None:
    repositorio = RotinasMemoria()

    async def valida(_: RotinaRequest) -> ResultadoValidacao:
        return ResultadoValidacao(True, intencao_prevista="consultar_riscos")

    class Scheduler:
        def __init__(self) -> None:
            self.jobs = []

        def add_job(self, *args, **kwargs) -> None:
            self.jobs.append((args, kwargs))

    scheduler = Scheduler()
    monkeypatch.setattr(rotas, "_validar_pedido", valida)
    monkeypatch.setattr(agendador, "_agendador", scheduler)
    pedido = RotinaRequest(
        nome="Riscos semanais",
        prompt="Liste os riscos críticos",
        agenda_cron="0 8 * * 1-5",
        timezone="America/Sao_Paulo",
    )
    resposta = await rotas.criar(pedido, USUARIO, repositorio)
    criada = repositorio.itens[resposta.id]
    agendador.agendar(criada)

    assert criada.agenda_cron == "0 8 * * 1-5"
    assert criada.timezone == "America/Sao_Paulo"
    assert scheduler.jobs[0][1]["id"] == f"rotina:{criada.id}"
    assert str(scheduler.jobs[0][1]["trigger"].timezone) == "America/Sao_Paulo"


async def test_tf_rf11_02_prompt_fora_do_catalogo_nao_cria_rotina(monkeypatch) -> None:
    repositorio = RotinasMemoria()

    async def invalida(_: RotinaRequest) -> ResultadoValidacao:
        return ResultadoValidacao(False, erro="Prompt fora do catálogo")

    monkeypatch.setattr(rotas, "_validar_pedido", invalida)
    pedido = RotinaRequest(nome="Inválida", prompt="Faça qualquer coisa", agenda_cron="0 8 * * 1")
    with pytest.raises(HTTPException) as erro:
        await rotas.criar(pedido, USUARIO, repositorio)
    assert erro.value.status_code == 422
    assert repositorio.itens == {}


async def test_tf_rf11_03_disparo_reavalia_prompt_e_identidade(monkeypatch) -> None:
    eventos = []

    async def inicio(*args) -> None:
        eventos.append("inicio")

    async def resolver(dono_id: str) -> UsuarioAutenticado:
        eventos.append(("resolver", dono_id))
        return USUARIO

    async def processar(rotina: Rotina, usuario: UsuarioAutenticado) -> ChatResponse:
        eventos.append(("pipeline", rotina.prompt, usuario.id))
        return ChatResponse(
            resposta="resultado",
            conversa_id="conv",
            desfecho=Desfecho.ENCAMINHADA.value,
            interacao_id="int",
        )

    async def fim(*args, **kwargs) -> None:
        eventos.append("fim")

    monkeypatch.setattr(execucao, "_registrar_inicio", inicio)
    monkeypatch.setattr(execucao, "_resolver_dono", resolver)
    monkeypatch.setattr(execucao, "_processar", processar)
    monkeypatch.setattr(execucao, "_registrar_fim", fim)
    await execucao.executar(_rotina())
    assert eventos == [
        "inicio",
        ("resolver", USUARIO.id),
        ("pipeline", "Liste os riscos críticos", USUARIO.id),
        "fim",
    ]


async def test_tf_rf11_04_permissao_revogada_falha_e_desativa(monkeypatch) -> None:
    registrado = {}

    async def inicio(*args) -> None:
        return None

    async def revogada(_: str):
        raise execucao.PermissaoRotinaRevogada("Permissão removida")

    async def falha(_, __, erro, *, desativar: bool) -> None:
        registrado.update(erro=erro, desativar=desativar)

    monkeypatch.setattr(execucao, "_registrar_inicio", inicio)
    monkeypatch.setattr(execucao, "_resolver_dono", revogada)
    monkeypatch.setattr(execucao, "_registrar_falha", falha)
    with pytest.raises(execucao.PermissaoRotinaRevogada):
        await execucao.executar(_rotina())
    assert registrado["desativar"] is True


async def test_tf_rf11_05_execucao_registra_estado_resultado_e_interacao(monkeypatch) -> None:
    conclusao = {}

    async def inicio(*args) -> None:
        return None

    async def resolver(_: str) -> UsuarioAutenticado:
        return USUARIO

    async def processar(*args) -> ChatResponse:
        return ChatResponse(
            resposta="Dois riscos críticos",
            conversa_id="conv",
            desfecho=Desfecho.ENCAMINHADA.value,
            interacao_id="interacao-rf11",
        )

    async def fim(_, **dados) -> None:
        conclusao.update(dados)

    monkeypatch.setattr(execucao, "_registrar_inicio", inicio)
    monkeypatch.setattr(execucao, "_resolver_dono", resolver)
    monkeypatch.setattr(execucao, "_processar", processar)
    monkeypatch.setattr(execucao, "_registrar_fim", fim)
    resposta = await execucao.executar(_rotina())
    assert conclusao == {
        "status": StatusExecucao.SUCESSO,
        "interacao_id": "interacao-rf11",
    }
    assert resposta.resposta == "Dois riscos críticos"


def test_tf_rf11_06_sem_permissao_nao_gerencia_rotinas() -> None:
    sem_permissao = UsuarioAutenticado("rf11-sem", "Sem permissão", Perfil.LIDER_PROJETO)
    app.dependency_overrides[deps.obter_usuario_atual] = lambda: sem_permissao
    try:
        with TestClient(app) as cliente:
            resposta = cliente.post(
                "/rotinas",
                json={
                    "nome": "Riscos",
                    "prompt": "Liste os riscos",
                    "agenda_cron": "0 8 * * 1",
                    "timezone": "America/Sao_Paulo",
                    "ativa": True,
                },
            )
        assert resposta.status_code == 403
    finally:
        app.dependency_overrides.clear()
