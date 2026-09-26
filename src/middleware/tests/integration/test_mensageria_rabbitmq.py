"""Topologia e produtor contra um RabbitMQ real.

Um dublê responderia o que combinamos com ele; aqui o que está em dúvida
é o broker: se a ligação leva cada evento à fila certa, se a rejeição
chega a `prata.failed` com a chave original e se a confirmação chega com
as propriedades que o consumidor vai ler.

Cada execução cria um vhost descartável pela API de gerenciamento e o
apaga no fim, levando filas e mensagens junto: nada toca as filas do
vhost de desenvolvimento, nem as consome de um `worker` em execução.
Exige o usuário administrador do Compose e o painel na porta 15672.

A suíte pula limpa quando o broker não responde. Para rodá-la:

    docker compose -f infra/docker-compose.yml up -d rabbitmq
"""

import asyncio
import json
from urllib.parse import quote, unquote, urlsplit, urlunsplit
from uuid import uuid4

import aio_pika
import httpx
import pytest
from aio_pika.exceptions import PublishError

from app.config import settings
from app.mensageria.produtor import ProdutorEventos, criar_evento
from app.mensageria.topologia import FILA_FALHAS, FILAS_TRABALHO, declarar_topologia

pytestmark = pytest.mark.integracao

# Porta do plugin de gerenciamento publicada pelo Compose.
PORTA_GERENCIAMENTO = 15672


@pytest.fixture
async def url_isolada():
    """URL AMQP de um vhost criado para o teste e apagado ao final."""
    url = urlsplit(settings.rabbitmq_url.get_secret_value())
    usuario, senha = unquote(url.username or ""), unquote(url.password or "")
    vhost = f"prata-teste-{uuid4().hex[:10]}"
    api = f"http://{url.hostname}:{PORTA_GERENCIAMENTO}/api"

    async with httpx.AsyncClient(auth=(usuario, senha), timeout=5) as cliente:
        try:
            criado = await cliente.put(f"{api}/vhosts/{vhost}")
        except httpx.HTTPError:
            pytest.skip(
                "RabbitMQ indisponível. Suba com "
                "`docker compose -f infra/docker-compose.yml up -d rabbitmq`."
            )
        if criado.status_code not in (201, 204):
            pytest.skip(f"Sem permissão para criar vhost de teste ({criado.status_code}).")
        try:
            await cliente.put(
                f"{api}/permissions/{vhost}/{quote(usuario, safe='')}",
                json={"configure": ".*", "write": ".*", "read": ".*"},
            )
            yield urlunsplit(url._replace(path="/" + quote(vhost, safe="")))
        finally:
            await cliente.delete(f"{api}/vhosts/{vhost}")


@pytest.fixture
async def canal(url_isolada):
    conexao = await aio_pika.connect(url_isolada)
    async with conexao:
        yield await conexao.channel(publisher_confirms=True, on_return_raises=True)


async def _receber(canal, nome: str):
    """Espera a mensagem chegar: a rejeição é roteada de forma assíncrona."""
    fila = await canal.declare_queue(nome, passive=True)
    for _ in range(50):
        mensagem = await fila.get(fail=False)
        if mensagem is not None:
            return mensagem
        await asyncio.sleep(0.1)
    pytest.fail(f"Nenhuma mensagem em {nome} após 5 s")


async def _topologia(canal):
    return await declarar_topologia(canal, "prata.events", "prata.dead-letter")


async def test_declaracao_repetida_e_idempotente(canal):
    await _topologia(canal)
    await _topologia(canal)

    for fila in FILAS_TRABALHO:
        await canal.declare_queue(fila.nome, passive=True)
    await canal.declare_queue(FILA_FALHAS, passive=True)


@pytest.mark.parametrize("fila", FILAS_TRABALHO, ids=lambda f: f.chave)
async def test_evento_chega_a_fila_e_rejeitado_vai_para_falhas(canal, fila):
    eventos = await _topologia(canal)

    await eventos.publish(aio_pika.Message(b"{}", message_id="m-1"), routing_key=fila.chave)
    recebida = await _receber(canal, fila.nome)
    await recebida.reject(requeue=False)

    morta = await _receber(canal, FILA_FALHAS)
    assert (morta.message_id, morta.routing_key) == ("m-1", fila.chave)
    await morta.ack()


async def test_evento_sem_fila_volta_ao_produtor(canal):
    eventos = await _topologia(canal)

    with pytest.raises(PublishError):
        await eventos.publish(aio_pika.Message(b"{}"), routing_key="evento.desconhecido")


async def test_produtor_publica_envelope_confirmado(url_isolada, canal):
    produtor = ProdutorEventos(url_isolada, "prata.events", "prata.dead-letter")
    evento = criar_evento("audio.transcription.requested", {"id_audio": "a-1"})
    try:
        await produtor.publicar(evento)
    finally:
        await produtor.encerrar()

    recebida = await _receber(canal, "prata.audio.transcription")
    await recebida.ack()
    assert recebida.message_id == str(evento.message_id)
    assert recebida.correlation_id == str(evento.correlation_id)
    assert recebida.delivery_mode == aio_pika.DeliveryMode.PERSISTENT
    assert recebida.type == "audio.transcription.requested"
    assert json.loads(recebida.body)["payload"] == {"id_audio": "a-1"}
