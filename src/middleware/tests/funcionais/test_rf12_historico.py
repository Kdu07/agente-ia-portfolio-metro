"""Casos TF-RF12-01 a TF-RF12-04 — histórico e retomada."""

from datetime import UTC, datetime

import pytest
from fastapi import HTTPException

from app.api.routes.conversas import detalhar, listar
from app.executor.base import RespostaExecutor
from app.persistence.models import Canal, Conversa, Interacao
from app.pipeline.desfechos import Desfecho
from app.pipeline.orquestrador import Orquestrador
from app.schemas.chat import ChatRequest
from app.schemas.usuario import Perfil, UsuarioAutenticado

AGORA = datetime.now(UTC)
USUARIO = UsuarioAutenticado("usuario-a", "Usuário A", Perfil.MEMBRO_EQUIPE)


def _conversa(conversa_id: str, usuario_id: str, titulo: str) -> Conversa:
    return Conversa(conversa_id, usuario_id, None, AGORA, AGORA, titulo)


class ConversasMemoria:
    def __init__(self) -> None:
        self.itens = {
            "conversa-a": _conversa("conversa-a", "usuario-a", "Status da Linha 15"),
            "conversa-b": _conversa("conversa-b", "usuario-b", "Conversa privada"),
        }

    async def listar_com_total_por_usuario(self, usuario_id: str, *, incluir_arquivadas=False):
        return [(item, 2) for item in self.itens.values() if item.usuario_id == usuario_id]

    async def obter(self, conversa_id: str, usuario_id: str):
        item = self.itens.get(conversa_id)
        return item if item and item.usuario_id == usuario_id else None


class InteracoesMemoria:
    def __init__(self) -> None:
        self.itens = [
            Interacao(
                "turno-1",
                "conversa-a",
                "usuario-a",
                Perfil.MEMBRO_EQUIPE.value,
                Canal.CHAT,
                "Qual o status?",
                "Em andamento",
                "consultar_status_projeto",
                0.95,
                Desfecho.ENCAMINHADA,
                10,
                AGORA,
            )
        ]

    async def salvar(self, interacao: Interacao) -> None:
        self.itens.append(interacao)

    async def listar_por_conversa(self, conversa_id: str, usuario_id: str, *, limite=None):
        itens = [
            item
            for item in self.itens
            if item.conversa_id == conversa_id and item.usuario_id == usuario_id
        ]
        return itens[-limite:] if limite else itens


async def test_tf_rf12_01_lista_somente_conversas_proprias_com_titulo() -> None:
    resposta = await listar(USUARIO, ConversasMemoria())
    assert [(item.id, item.titulo) for item in resposta] == [
        ("conversa-a", "Status da Linha 15")
    ]


async def test_tf_rf12_02_retomada_entrega_historico_ao_executor(
    pipeline_controlado,
) -> None:
    conversas = ConversasMemoria()
    interacoes = InteracoesMemoria()
    recebido = {}

    class Executor:
        async def enviar(self, texto, intencao_id, exige_confirmacao, conversa_externa_id, historico):
            recebido["historico"] = historico
            return RespostaExecutor(texto="Continuação contextualizada")

    pipeline = Orquestrador(Executor(), interacoes, conversas)
    resposta = await pipeline.processar(
        ChatRequest(mensagem="E os riscos?", conversa_id="conversa-a"), USUARIO
    )
    assert resposta.desfecho == Desfecho.ENCAMINHADA.value
    assert recebido["historico"][0].mensagem_usuario == "Qual o status?"
    assert recebido["historico"][0].resposta_agente == "Em andamento"


async def test_tf_rf12_03_conversa_alheia_retorna_404() -> None:
    with pytest.raises(HTTPException) as erro:
        await detalhar("conversa-b", USUARIO, ConversasMemoria(), InteracoesMemoria())
    assert (erro.value.status_code, erro.value.detail) == (404, "Conversa não encontrada")


async def test_tf_rf12_04_conversa_alheia_e_inexistente_sao_indistinguiveis() -> None:
    respostas = []
    for conversa_id in ("conversa-b", "nao-existe"):
        try:
            await detalhar(conversa_id, USUARIO, ConversasMemoria(), InteracoesMemoria())
        except HTTPException as erro:
            respostas.append((erro.status_code, erro.detail))
    assert respostas == [(404, "Conversa não encontrada"), (404, "Conversa não encontrada")]
