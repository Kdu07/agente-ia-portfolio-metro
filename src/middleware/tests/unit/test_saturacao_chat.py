"""Regressões dos gargalos identificados na bancada de carga do chat."""

import json
from datetime import UTC, datetime

import pytest
from fastapi import Request
from sqlalchemy.exc import TimeoutError as SQLAlchemyTimeoutError

from app.config import settings
from app.main import tratar_pool_esgotado
from app.persistence import repository
from app.persistence.models import Canal, Conversa, Interacao
from app.pipeline import orquestrador as modulo_orquestrador
from app.pipeline.desfechos import Desfecho
from app.pipeline.orquestrador import Orquestrador, _Contexto
from app.schemas.usuario import Perfil, UsuarioAutenticado


async def test_repositorio_transacional_devolve_conexao_apos_operacao(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    eventos = []

    class Sessao:
        async def __aenter__(self):
            eventos.append("abriu")
            return self

        async def __aexit__(self, *args):
            eventos.append("fechou")

        async def commit(self):
            eventos.append("commit")

        async def rollback(self):
            eventos.append("rollback")

    async def obter(self, conversa_id, usuario_id):
        eventos.append("consultou")

    monkeypatch.setattr(repository.ConversaRepository, "obter", obter)
    adaptador = repository.ConversaRepositoryTransacional(lambda: Sessao())

    assert await adaptador.obter("c1", "u1") is None
    assert eventos == ["abriu", "consultou", "commit", "fechou"]


async def test_pool_esgotado_responde_503_sem_expor_detalhes() -> None:
    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/chat",
            "headers": [],
            "query_string": b"",
            "server": ("test", 80),
            "client": ("test", 123),
            "scheme": "http",
        }
    )

    resposta = await tratar_pool_esgotado(
        request, SQLAlchemyTimeoutError("QueuePool limit; segredo-interno")
    )

    assert resposta.status_code == 503
    assert resposta.headers["Retry-After"] == "2"
    assert json.loads(resposta.body) == {
        "detail": "Serviço temporariamente ocupado. Tente novamente em instantes."
    }
    assert b"segredo-interno" not in resposta.body


async def test_historico_persistido_nao_repete_chamada_externa(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    usuario = UsuarioAutenticado(id="u1", nome="Usuária", perfil=Perfil.LIDER_PROJETO)
    agora = datetime.now(UTC)
    conversa = Conversa("c1", usuario.id, None, agora, agora, "Contexto")
    turno = Interacao(
        "i1",
        conversa.id,
        usuario.id,
        usuario.perfil.value,
        Canal.CHAT,
        "Qual o prazo?",
        "O prazo é sexta-feira.",
        "consultar_cronograma_projeto",
        0.95,
        Desfecho.ENCAMINHADA,
        10,
        agora,
    )
    bloqueado_pelo_modelo = Interacao(
        "i0",
        conversa.id,
        usuario.id,
        usuario.perfil.value,
        Canal.CHAT,
        "Texto obfuscado detectado apenas pelo modelo",
        "Solicitação bloqueada.",
        None,
        0.0,
        Desfecho.BLOQUEADA_INJECAO_MODELO,
        10,
        agora,
    )

    class Interacoes:
        async def listar_por_conversa(self, *args, **kwargs):
            return [bloqueado_pelo_modelo, turno]

    async def chamada_externa_indevida(*args, **kwargs):
        raise AssertionError("histórico persistido não deve consumir Content Safety")

    monkeypatch.setattr(settings, "historico_max_turnos", 3)
    monkeypatch.setattr(
        modulo_orquestrador.injecao_regras,
        "contem_padrao_suspeito",
        lambda texto: False,
    )
    monkeypatch.setattr(
        modulo_orquestrador.injecao_classificador,
        "classificar",
        chamada_externa_indevida,
    )
    pipeline = Orquestrador(object(), Interacoes(), object())
    contexto = _Contexto("atual", conversa, usuario, Canal.CHAT, "E o orçamento?")

    historico = await pipeline._historico_seguro(contexto)

    assert len(historico) == 1
    assert historico[0].mensagem_usuario == "Qual o prazo?"
