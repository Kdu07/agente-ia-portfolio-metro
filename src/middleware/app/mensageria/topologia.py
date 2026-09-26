"""Topologia do RabbitMQ descrita na seção 9.1.2.6 do Projeto.md.

A declaração é idempotente: produtor e consumidor podem chamá-la na
subida, em qualquer ordem, sem depender de quem chegou primeiro. Um
argumento diferente numa fila já existente faz o broker recusar a
declaração (PRECONDITION_FAILED); por isso os argumentos das filas só
mudam junto com uma migração da topologia.

A fila de falhas é ligada ao exchange de mensagens mortas pelas mesmas
chaves das filas de trabalho. Assim a mensagem rejeitada chega a
`prata.failed` com a chave original, e a inspeção sabe de onde ela veio.

Retentativa com atraso crescente (9.1.2.6): cada fila de trabalho tem uma
fila de espera por tentativa (`<fila>.retry.<n>`), ligada ao exchange
`prata.retry`, com TTL fixo e dead letter de volta a `prata.events` com a
chave original. Um TTL por fila, e não por mensagem, é o que impede uma
mensagem com espera longa de segurar outra de espera curta atrás dela:
o RabbitMQ só expira a mensagem que está na frente da fila.
"""

from dataclasses import dataclass

from aio_pika import ExchangeType
from aio_pika.abc import AbstractChannel, AbstractExchange


@dataclass(frozen=True)
class FilaTrabalho:
    """Fila durável que recebe um único tipo de evento."""

    nome: str
    chave: str


AUDIO_TRANSCRICAO = FilaTrabalho("prata.audio.transcription", "audio.transcription.requested")
ROTINA_EXECUCAO = FilaTrabalho("prata.routines.execution", "routine.execution.requested")
WEBHOOK_RECEBIDO = FilaTrabalho("prata.webhooks.incoming", "webhook.received")

FILAS_TRABALHO = (AUDIO_TRANSCRICAO, ROTINA_EXECUCAO, WEBHOOK_RECEBIDO)
FILA_FALHAS = "prata.failed"

EXCHANGE_RETENTATIVA = "prata.retry"
# Espera antes de cada nova tentativa, em segundos. O consumidor usa as
# primeiras `RABBITMQ_MAX_RETRIES`; tentativas além da tabela repetem a última.
ESPERAS_RETENTATIVA = (5, 20, 60, 300, 900)


def fila_retentativa(fila: FilaTrabalho, tentativa: int) -> str:
    """Nome (e chave de roteamento) da fila de espera da tentativa `n` (1..)."""
    nivel = min(max(tentativa, 1), len(ESPERAS_RETENTATIVA))
    return f"{fila.nome}.retry.{nivel}"


async def declarar_topologia(
    canal: AbstractChannel, exchange: str, dead_letter_exchange: str
) -> AbstractExchange:
    """Declara exchanges, filas e ligações; devolve o exchange de eventos."""
    eventos = await canal.declare_exchange(exchange, ExchangeType.TOPIC, durable=True)
    mortas = await canal.declare_exchange(dead_letter_exchange, ExchangeType.DIRECT, durable=True)
    retentativa = await canal.declare_exchange(
        EXCHANGE_RETENTATIVA, ExchangeType.DIRECT, durable=True
    )
    falhas = await canal.declare_queue(FILA_FALHAS, durable=True)

    for fila in FILAS_TRABALHO:
        trabalho = await canal.declare_queue(
            fila.nome,
            durable=True,
            arguments={"x-dead-letter-exchange": dead_letter_exchange},
        )
        await trabalho.bind(eventos, routing_key=fila.chave)
        await falhas.bind(mortas, routing_key=fila.chave)
        for tentativa, espera in enumerate(ESPERAS_RETENTATIVA, start=1):
            nome = fila_retentativa(fila, tentativa)
            espera_fila = await canal.declare_queue(
                nome,
                durable=True,
                arguments={
                    "x-message-ttl": espera * 1000,
                    "x-dead-letter-exchange": exchange,
                    "x-dead-letter-routing-key": fila.chave,
                },
            )
            await espera_fila.bind(retentativa, routing_key=nome)

    return eventos
