"""Integração HTTP das rotas de histórico e isolamento por usuário."""

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from app.api import deps
from app.main import app
from app.persistence.models import Canal, Conversa, Interacao
from app.pipeline.desfechos import Desfecho
from app.schemas.usuario import Perfil, UsuarioAutenticado


def _usuario(usuario_id: str) -> UsuarioAutenticado:
    return UsuarioAutenticado(id=usuario_id, nome=usuario_id, perfil=Perfil.MEMBRO_EQUIPE)


class RepositorioConversasMemoria:
    def __init__(self) -> None:
        agora = datetime.now(UTC)
        self.conversas = {
            "conversa-a": Conversa("conversa-a", "usuario-a", None, agora, agora, "A"),
            "conversa-b": Conversa("conversa-b", "usuario-b", None, agora, agora, "B"),
        }
        self.interacoes = {
            "conversa-a": [
                Interacao(
                    "turno-a",
                    "conversa-a",
                    "usuario-a",
                    Perfil.MEMBRO_EQUIPE.value,
                    Canal.CHAT,
                    "Pergunta A",
                    "Resposta A",
                    "consultar_status_projeto",
                    0.9,
                    Desfecho.ENCAMINHADA,
                    100,
                    agora,
                )
            ],
            "conversa-b": [],
        }

    async def listar_por_usuario(self, usuario_id: str, *, incluir_arquivadas: bool = False):
        return [
            conversa
            for conversa in self.conversas.values()
            if conversa.usuario_id == usuario_id
            and (incluir_arquivadas or conversa.arquivada_em is None)
        ]

    async def obter(self, conversa_id: str, usuario_id: str):
        conversa = self.conversas.get(conversa_id)
        return conversa if conversa and conversa.usuario_id == usuario_id else None

    async def contar_interacoes(self, conversa_id: str, usuario_id: str) -> int:
        conversa = await self.obter(conversa_id, usuario_id)
        return len(self.interacoes.get(conversa_id, [])) if conversa else 0

    async def arquivar(self, conversa_id: str, usuario_id: str) -> None:
        conversa = await self.obter(conversa_id, usuario_id)
        if conversa:
            conversa.arquivada_em = datetime.now(UTC)


class InteracoesMemoria:
    def __init__(self, repositorio: RepositorioConversasMemoria) -> None:
        self.repositorio = repositorio

    async def listar_por_conversa(self, conversa_id: str, usuario_id: str):
        conversa = await self.repositorio.obter(conversa_id, usuario_id)
        return self.repositorio.interacoes.get(conversa_id, []) if conversa else []


@pytest.fixture
def api_conversas():
    repositorio = RepositorioConversasMemoria()
    usuario = _usuario("usuario-a")
    app.dependency_overrides[deps.obter_usuario_atual] = lambda: usuario
    app.dependency_overrides[deps.obter_conversas] = lambda: repositorio
    app.dependency_overrides[deps.obter_interacoes] = lambda: InteracoesMemoria(repositorio)
    with TestClient(app) as client:
        yield client, repositorio
    app.dependency_overrides.clear()


def test_usuario_ve_apenas_as_proprias_conversas(api_conversas):
    client, _ = api_conversas
    resposta = client.get("/conversas")
    assert resposta.status_code == 200
    assert [item["id"] for item in resposta.json()] == ["conversa-a"]


def test_usuario_nao_acessa_detalhe_de_outro(api_conversas):
    client, _ = api_conversas
    assert client.get("/conversas/conversa-b").status_code == 404


def test_usuario_nao_arquiva_conversa_de_outro(api_conversas):
    client, repositorio = api_conversas
    assert client.delete("/conversas/conversa-b").status_code == 404
    assert repositorio.conversas["conversa-b"].arquivada_em is None


def test_usuario_arquiva_a_propria_conversa_e_ela_some_da_lista(api_conversas):
    client, _ = api_conversas
    assert client.delete("/conversas/conversa-a").status_code == 204
    assert client.get("/conversas").json() == []


def test_acesso_sem_sessao_retorna_401():
    with TestClient(app) as client:
        assert client.get("/conversas").status_code == 401