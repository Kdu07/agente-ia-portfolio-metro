"""Regressões dos gargalos identificados na bancada de carga do chat."""

import json
from datetime import UTC, datetime

import pytest
from fastapi import Request
from sqlalchemy.exc import TimeoutError as SQLAlchemyTimeoutError
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.config import settings
from app.main import tratar_pool_esgotado
from app.persistence import repository
from app.persistence.models import Canal, Conversa, Interacao
from app.pipeline import orquestrador as modulo_orquestrador
from app.pipeline.desfechos import Desfecho
from app.pipeline.orquestrador import Orquestrador, _Contexto
from app.rag import recuperacao
from app.rag.ingestao.registro import RegistroIngestao
from app.rag.vetorial import fabrica as fabrica_vetorial
from app.rag.vetorial.base import Escopo
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


async def test_recuperador_do_chat_fecha_cada_sessao_antes_de_devolver(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Com a fábrica, nenhuma leitura do RAG deixa conexão presa para a geração."""
    eventos = []

    class Sessao:
        def __init__(self, **_opcoes) -> None:
            """O `async_sessionmaker` repassa bind e opções; aqui não importam."""

        async def __aenter__(self):
            eventos.append("abriu")
            return self

        async def __aexit__(self, *args):
            eventos.append("fechou")

    class Vetorial:
        async def buscar(self, vetor, **kwargs):
            eventos.append("buscou")
            return ()

    async def textos(self, trecho_ids):
        eventos.append("leu")
        return {}

    monkeypatch.setattr(fabrica_vetorial, "obter_repositorio_vetorial", lambda sessao: Vetorial())
    monkeypatch.setattr(RegistroIngestao, "textos", textos)
    recuperador = recuperacao.montar_recuperador(async_sessionmaker(class_=Sessao))
    recuperador._codificar = lambda texto: [0.0]

    resultado = await recuperador.recuperar(
        "Qual o prazo do Trecho Sul?", Escopo(perfil=Perfil.LIDER_PROJETO)
    )

    assert resultado.vazia
    assert eventos == ["abriu", "buscou", "fechou", "abriu", "leu", "fechou"]
