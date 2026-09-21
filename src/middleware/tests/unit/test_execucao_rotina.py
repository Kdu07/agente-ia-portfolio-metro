"""Execução de rotinas: estado, pipeline e falhas do dono."""

from datetime import UTC, datetime

import pytest

from app.auth import entra
from app.persistence.models import Rotina, StatusExecucao
from app.pipeline.desfechos import Desfecho
from app.rotinas import execucao
from app.schemas.chat import ChatResponse
from app.schemas.usuario import Perfil, UsuarioAutenticado

ROTINA = Rotina(
    id="rot-1",
    nome="Relatório semanal",
    prompt="Liste os riscos críticos do meu projeto",
    agenda_cron="0 8 * * 1",
    timezone="America/Sao_Paulo",
    dono_id="dono-1",
    ativa=True,
    criada_em=datetime.now(UTC),
    atualizada_em=datetime.now(UTC),
)
USUARIO = UsuarioAutenticado(id="dono-1", nome="Dono", perfil=Perfil.LIDER_PROJETO)


def _resposta(desfecho: Desfecho) -> ChatResponse:
    return ChatResponse(
        resposta="resultado",
        conversa_id="conv-1",
        desfecho=desfecho.value,
        bloqueada=desfecho.bloqueada,
        interacao_id="int-1",
    )


async def test_execucao_com_sucesso_registra_inicio_pipeline_e_fim(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    eventos: list[tuple] = []

    async def inicio(execucao_id: str, rotina_id: str) -> None:
        eventos.append(("inicio", execucao_id, rotina_id))

    async def resolver(dono_id: str) -> UsuarioAutenticado:
        eventos.append(("resolver", dono_id))
        return USUARIO

    async def processar(rotina: Rotina, usuario: UsuarioAutenticado) -> ChatResponse:
        eventos.append(("pipeline", rotina.id, usuario.id))
        return _resposta(Desfecho.ENCAMINHADA)

    async def fim(execucao_id: str, **dados) -> None:
        eventos.append(("fim", execucao_id, dados["status"], dados["interacao_id"]))

    monkeypatch.setattr(execucao, "_registrar_inicio", inicio)
    monkeypatch.setattr(execucao, "_resolver_dono", resolver)
    monkeypatch.setattr(execucao, "_processar", processar)
    monkeypatch.setattr(execucao, "_registrar_fim", fim)

    resposta = await execucao.executar(ROTINA)

    assert resposta.desfecho == Desfecho.ENCAMINHADA.value
    assert "interacao_id" not in resposta.model_dump()
    assert [evento[0] for evento in eventos] == ["inicio", "resolver", "pipeline", "fim"]
    assert eventos[-1][2:] == (StatusExecucao.SUCESSO, "int-1")


async def test_prompt_barrado_e_registrado_como_bloqueado(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    conclusao: dict = {}

    async def ignorar(*args, **kwargs) -> None:
        return None

    async def resolver(dono_id: str) -> UsuarioAutenticado:
        return USUARIO

    async def processar(rotina: Rotina, usuario: UsuarioAutenticado) -> ChatResponse:
        return _resposta(Desfecho.BLOQUEADA_ABUSO)

    async def fim(execucao_id: str, **dados) -> None:
        conclusao.update(dados)

    monkeypatch.setattr(execucao, "_registrar_inicio", ignorar)
    monkeypatch.setattr(execucao, "_resolver_dono", resolver)
    monkeypatch.setattr(execucao, "_processar", processar)
    monkeypatch.setattr(execucao, "_registrar_fim", fim)

    await execucao.executar(ROTINA)

    assert conclusao["status"] is StatusExecucao.BLOQUEADA
    assert conclusao["interacao_id"] == "int-1"


@pytest.mark.parametrize(
    ("erro", "desativa"),
    [
        (entra.FalhaConsultaDiretorio("Graph indisponível"), False),
        (entra.UsuarioEntraInativo("Dono desativado"), True),
        (execucao.PermissaoRotinaRevogada("Permissão removida"), True),
    ],
)
async def test_falha_e_registrada_e_so_revogacao_permanente_desativa(
    monkeypatch: pytest.MonkeyPatch,
    erro: Exception,
    desativa: bool,
) -> None:
    gravada: dict = {}

    async def ignorar(*args, **kwargs) -> None:
        return None

    async def falhar(dono_id: str) -> UsuarioAutenticado:
        raise erro

    async def registrar(execucao_id: str, rotina: Rotina, recebido: Exception, **dados) -> None:
        gravada.update(erro=recebido, desativar=dados["desativar"])

    monkeypatch.setattr(execucao, "_registrar_inicio", ignorar)
    monkeypatch.setattr(execucao, "_resolver_dono", falhar)
    monkeypatch.setattr(execucao, "_registrar_falha", registrar)

    with pytest.raises(type(erro)):
        await execucao.executar(ROTINA)

    assert gravada == {"erro": erro, "desativar": desativa}


async def test_processamento_entra_no_orquestrador_com_canal_rotina(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    chamada: dict = {}

    class Sessao:
        async def commit(self) -> None:
            chamada["commit"] = True

        async def rollback(self) -> None:
            chamada["rollback"] = True

    class Contexto:
        async def __aenter__(self) -> Sessao:
            return Sessao()

        async def __aexit__(self, *args) -> None:
            return None

    class OrquestradorFake:
        def __init__(self, **kwargs) -> None:
            chamada["dependencias"] = kwargs

        async def processar(self, pedido, usuario, **kwargs) -> ChatResponse:
            chamada.update(pedido=pedido, usuario=usuario, argumentos=kwargs)
            return _resposta(Desfecho.ENCAMINHADA)

    monkeypatch.setattr(execucao, "fabrica_de_sessoes", lambda: lambda: Contexto())
    monkeypatch.setattr(execucao, "montar_executor", lambda sessao, usuario: object())
    monkeypatch.setattr(execucao, "Orquestrador", OrquestradorFake)

    await execucao._processar(ROTINA, USUARIO)

    assert chamada["pedido"].mensagem == ROTINA.prompt
    assert chamada["argumentos"]["rotina_id"] == ROTINA.id
    assert chamada["argumentos"]["canal"].value == "rotina"
    assert chamada["commit"] is True


async def test_execucao_manual_nao_permite_usar_identidade_de_outro_dono(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Contexto:
        async def __aenter__(self) -> object:
            return object()

        async def __aexit__(self, *args) -> None:
            return None

    class RotinasFake:
        def __init__(self, sessao) -> None:
            pass

        async def obter(self, rotina_id: str) -> Rotina:
            return ROTINA

    monkeypatch.setattr(execucao, "fabrica_de_sessoes", lambda: lambda: Contexto())
    monkeypatch.setattr(execucao, "RotinaRepository", RotinasFake)

    with pytest.raises(execucao.ExecucaoNaoAutorizada):
        await execucao.executar_agora(ROTINA.id, "outro-usuario")
