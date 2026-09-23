"""Testes do produtor de eventos AMQP com broker dublado.

O broker real fica em tests/integration/test_mensageria_rabbitmq.py.
Aqui a conexão e o exchange são dublês, o que permite provocar cada
falha de forma determinística: recusa de conexão, confirmação que não
chega e topologia que falha no meio da declaração.
"""

import asyncio
from datetime import UTC
from types import SimpleNamespace
from uuid import uuid4

import pytest
from aio_pika import DeliveryMode
from aio_pika.exceptions import AMQPConnectionError, DeliveryError
from fastapi.testclient import TestClient

from app.api import deps
from app.main import app
from app.mensageria import produtor as modulo
from app.mensageria.produtor import FalhaPublicacao, ProdutorEventos, criar_evento

URL = "amqp://emissor:senha-sintetica@broker.teste:5672/prata"


class ExchangeFalso:
    def __init__(self, erro: BaseException | None = None) -> None:
        self.erro = erro
        self.publicadas: list[tuple] = []

    async def publish(self, mensagem, routing_key, *, mandatory, timeout):
        if self.erro is not None:
            raise self.erro
        self.publicadas.append((mensagem, routing_key, mandatory, timeout))


class ConexaoFalsa:
    def __init__(self) -> None:
        self.fechada = False
        self.canais: list[dict] = []

    async def channel(self, **opcoes):
        self.canais.append(opcoes)
        return object()

    async def close(self) -> None:
        self.fechada = True


@pytest.fixture
def broker(monkeypatch):
    """Substitui conexão e topologia; devolve o estado para inspeção."""

    estado = SimpleNamespace(
        conexoes=[], exchange=ExchangeFalso(), erro_conexao=None, erro_topologia=None
    )

    async def conectar(url, *, timeout):
        await asyncio.sleep(0)  # cede a vez, como uma conexão de rede
        if estado.erro_conexao is not None:
            raise estado.erro_conexao
        conexao = ConexaoFalsa()
        estado.conexoes.append(conexao)
        return conexao

    async def declarar(canal, exchange, dead_letter_exchange):
        if estado.erro_topologia is not None:
            raise estado.erro_topologia
        return estado.exchange

    monkeypatch.setattr(modulo.aio_pika, "connect_robust", conectar)
    monkeypatch.setattr(modulo, "declarar_topologia", declarar)
    return estado


def produtor() -> ProdutorEventos:
    return ProdutorEventos(URL, "prata.events", "prata.dead-letter", timeout_segundos=1)


def test_criar_evento_gera_identificadores_e_data_utc():
    evento = criar_evento("webhook.received", {"origem": "drive"})

    assert evento.message_id != evento.correlation_id
    assert evento.occurred_at.tzinfo == UTC
    assert (evento.schema_version, evento.producer) == (1, "middleware")


def test_criar_evento_preserva_correlacao_da_origem():
    origem = uuid4()

    assert criar_evento("webhook.received", {}, correlation_id=origem).correlation_id == origem


async def test_publica_mensagem_persistente_com_identificadores(broker):
    evento = criar_evento("audio.transcription.requested", {"id_audio": "a-1"})

    await produtor().publicar(evento)

    [(mensagem, chave, mandatory, timeout)] = broker.exchange.publicadas
    assert (chave, mandatory, timeout) == ("audio.transcription.requested", True, 1)
    assert mensagem.delivery_mode == DeliveryMode.PERSISTENT
    assert mensagem.message_id == str(evento.message_id)
    assert mensagem.correlation_id == str(evento.correlation_id)
    assert (mensagem.type, mensagem.app_id) == ("audio.transcription.requested", "middleware")
    assert (mensagem.content_type, mensagem.headers) == ("application/json", {"schema_version": 1})
    assert mensagem.body == evento.model_dump_json().encode("utf-8")


async def test_canal_exige_confirmacao_e_devolucao_de_mensagem_sem_rota(broker):
    await produtor().publicar(criar_evento("webhook.received", {}))

    assert broker.conexoes[0].canais == [{"publisher_confirms": True, "on_return_raises": True}]


async def test_recusa_tipo_sem_fila_antes_de_conectar(broker):
    with pytest.raises(ValueError, match="sem fila"):
        await produtor().publicar(criar_evento("evento.desconhecido", {}))

    assert broker.conexoes == []


@pytest.mark.parametrize(
    "onde,erro",
    [
        ("erro_conexao", AMQPConnectionError("recusada")),
        ("erro_conexao", TimeoutError()),
        ("erro_topologia", AMQPConnectionError("caiu na declaração")),
    ],
)
async def test_falha_ao_conectar_vira_erro_transitorio(broker, onde, erro):
    setattr(broker, onde, erro)
    evento = criar_evento("webhook.received", {})

    with pytest.raises(FalhaPublicacao) as falha:
        await produtor().publicar(evento)

    assert (falha.value.message_id, falha.value.correlation_id) == (
        evento.message_id,
        evento.correlation_id,
    )
    assert "senha-sintetica" not in str(falha.value)


@pytest.mark.parametrize("erro", [DeliveryError(None, None), TimeoutError()])
async def test_confirmacao_ausente_vira_erro_transitorio(broker, erro):
    broker.exchange = ExchangeFalso(erro)

    with pytest.raises(FalhaPublicacao):
        await produtor().publicar(criar_evento("webhook.received", {}))


async def test_topologia_que_falha_fecha_a_conexao_aberta(broker):
    broker.erro_topologia = AMQPConnectionError("caiu na declaração")

    with pytest.raises(FalhaPublicacao):
        await produtor().publicar(criar_evento("webhook.received", {}))

    assert broker.conexoes[0].fechada


async def test_publicacoes_concorrentes_abrem_uma_unica_conexao(broker):
    alvo = produtor()

    await asyncio.gather(*(alvo.publicar(criar_evento("webhook.received", {})) for _ in range(5)))

    assert len(broker.conexoes) == 1
    assert len(broker.exchange.publicadas) == 5


async def test_encerrar_fecha_e_proxima_publicacao_reconecta(broker):
    alvo = produtor()
    await alvo.publicar(criar_evento("webhook.received", {}))

    await alvo.encerrar()
    await alvo.publicar(criar_evento("webhook.received", {}))

    assert [c.fechada for c in broker.conexoes] == [True, False]


async def test_nova_tentativa_conecta_depois_de_falha(broker):
    alvo = produtor()
    broker.erro_conexao = AMQPConnectionError("recusada")
    with pytest.raises(FalhaPublicacao):
        await alvo.publicar(criar_evento("webhook.received", {}))

    broker.erro_conexao = None
    await alvo.publicar(criar_evento("webhook.received", {}))

    assert len(broker.exchange.publicadas) == 1


def test_lifespan_cria_produtor_sem_conectar_e_dependencia_o_entrega(monkeypatch):
    async def conexao_proibida(*args, **kwargs):
        raise AssertionError("o lifespan não deve conectar ao broker")

    monkeypatch.setattr(modulo.aio_pika, "connect_robust", conexao_proibida)

    with TestClient(app):
        criado = app.state.produtor_eventos

        assert isinstance(criado, ProdutorEventos)
        assert deps.obter_produtor(SimpleNamespace(app=app)) is criado
