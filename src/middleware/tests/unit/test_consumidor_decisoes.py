"""Decisões do consumidor de webhooks com mensagem e broker dublados.

O que se verifica aqui é a escolha entre `ack`, retentativa e descarte
(Projeto.md 9.1.2.6): sucesso confirma uma vez; falha definitiva rejeita
sem repor, e o dead letter leva a `prata.failed`; falha transitória vai
para a fila de espera da tentativa seguinte, com o cabeçalho de tentativa,
até esgotar `RABBITMQ_MAX_RETRIES`. O ciclo com banco e broker reais está
em tests/integration/test_consumidor_webhooks.py.
"""

import asyncio

import pytest

from app.mensageria import consumidor as modulo
from app.mensageria.consumidor import CABECALHO_TENTATIVA, ConsumidorWebhooks, FalhaDefinitiva
from app.mensageria.produtor import criar_evento
from app.webhooks.drive.sincronizacao import SincronizacaoDrive


class MensagemFalsa:
    def __init__(self, corpo: bytes, cabecalhos: dict | None = None) -> None:
        self.body = corpo
        self.headers = cabecalhos or {}
        self.message_id = "m-1"
        self.correlation_id = "c-1"
        self.content_type = "application/json"
        self.content_encoding = "utf-8"
        self.type = "webhook.received"
        self.app_id = "middleware"
        self.timestamp = None
        self.decisoes: list[tuple] = []

    async def ack(self):
        self.decisoes.append(("ack",))

    async def reject(self, requeue):
        self.decisoes.append(("reject", requeue))

    async def nack(self, requeue):
        self.decisoes.append(("nack", requeue))


class ExchangeFalso:
    def __init__(self, falhar: bool = False) -> None:
        self.falhar = falhar
        self.publicadas: list[tuple] = []

    async def publish(self, mensagem, routing_key, timeout):
        if self.falhar:
            raise ConnectionError("broker fora")
        self.publicadas.append((mensagem, routing_key))


def evento_valido() -> bytes:
    return criar_evento("webhook.received", {"provider": "google_drive"}).model_dump_json().encode()


@pytest.fixture
def consumidor(monkeypatch):
    alvo = ConsumidorWebhooks(
        "amqp://x",
        exchange="prata.events",
        dead_letter_exchange="prata.dead-letter",
        fabrica=None,
        tratadores={},
        max_retries=2,
        prefetch=10,
    )
    alvo.falhas: list[str] = []
    alvo.resultado = True

    async def executar(evento):
        if isinstance(alvo.resultado, BaseException):
            raise alvo.resultado
        return alvo.resultado

    async def registrar(evento, codigo):
        alvo.falhas.append(codigo)

    monkeypatch.setattr(alvo, "_executar_tratador", executar)
    monkeypatch.setattr(alvo, "_registrar_falha", registrar)
    alvo._retentativa = ExchangeFalso()
    return alvo


async def test_sucesso_confirma_uma_vez(consumidor):
    mensagem = MensagemFalsa(evento_valido())

    await consumidor.processar(mensagem)

    assert mensagem.decisoes == [("ack",)]


async def test_ja_processado_so_confirma(consumidor):
    consumidor.resultado = False
    mensagem = MensagemFalsa(evento_valido())

    await consumidor.processar(mensagem)

    assert mensagem.decisoes == [("ack",)]
    assert consumidor.falhas == []


async def test_envelope_invalido_vai_para_descarte_sem_executar(consumidor):
    consumidor.resultado = AssertionError("não deveria executar")
    mensagem = MensagemFalsa(b"nao e json")

    await consumidor.processar(mensagem)

    assert mensagem.decisoes == [("reject", False)]


async def test_falha_definitiva_rejeita_sem_repor_e_registra(consumidor):
    consumidor.resultado = FalhaDefinitiva("CONFLITO_DE_VERSAO")
    mensagem = MensagemFalsa(evento_valido())

    await consumidor.processar(mensagem)

    assert mensagem.decisoes == [("reject", False)]
    assert consumidor.falhas == ["CONFLITO_DE_VERSAO"]
    assert consumidor._retentativa.publicadas == []


async def test_falha_transitoria_vai_para_a_primeira_espera(consumidor):
    consumidor.resultado = ConnectionError("serviço fora")
    mensagem = MensagemFalsa(evento_valido())

    await consumidor.processar(mensagem)

    [(copia, chave)] = consumidor._retentativa.publicadas
    assert chave == "prata.webhooks.incoming.retry.1"
    assert copia.headers[CABECALHO_TENTATIVA] == 1
    assert (copia.message_id, copia.body) == (mensagem.message_id, mensagem.body)
    assert mensagem.decisoes == [("ack",)]
    assert consumidor.falhas == ["PROCESSAMENTO_TRANSITORIO"]


async def test_segunda_falha_vai_para_a_espera_seguinte(consumidor):
    consumidor.resultado = ConnectionError("serviço fora")
    mensagem = MensagemFalsa(evento_valido(), {CABECALHO_TENTATIVA: 1})

    await consumidor.processar(mensagem)

    [(copia, chave)] = consumidor._retentativa.publicadas
    assert (chave, copia.headers[CABECALHO_TENTATIVA]) == ("prata.webhooks.incoming.retry.2", 2)


async def test_retentativas_esgotadas_vao_para_descarte(consumidor):
    consumidor.resultado = ConnectionError("serviço fora")
    mensagem = MensagemFalsa(evento_valido(), {CABECALHO_TENTATIVA: 2})

    await consumidor.processar(mensagem)

    assert mensagem.decisoes == [("reject", False)]
    assert consumidor._retentativa.publicadas == []


async def test_sem_confirmar_a_copia_a_original_volta_a_fila(consumidor):
    consumidor.resultado = ConnectionError("serviço fora")
    consumidor._retentativa = ExchangeFalso(falhar=True)
    mensagem = MensagemFalsa(evento_valido())

    await consumidor.processar(mensagem)

    assert mensagem.decisoes == [("nack", True)]


async def test_encerrar_espera_a_mensagem_em_curso(consumidor, monkeypatch):
    liberar = asyncio.Event()

    async def demorado(evento):
        await liberar.wait()
        return True

    monkeypatch.setattr(consumidor, "_executar_tratador", demorado)
    mensagem = MensagemFalsa(evento_valido())
    em_curso = asyncio.create_task(consumidor.processar(mensagem))
    await asyncio.sleep(0)

    encerramento = asyncio.create_task(consumidor.encerrar(prazo_segundos=5))
    await asyncio.sleep(0.05)
    assert not encerramento.done()
    liberar.set()
    await asyncio.wait_for(encerramento, 1)
    await em_curso

    assert mensagem.decisoes == [("ack",)]


def test_executar_reconecta_quando_o_broker_nao_responde(monkeypatch):
    tentativas = []

    async def iniciar_falhando():
        tentativas.append(1)
        raise ConnectionError("recusada")

    alvo = ConsumidorWebhooks(
        "amqp://x",
        exchange="e",
        dead_letter_exchange="d",
        fabrica=None,
        tratadores={},
        max_retries=2,
        prefetch=1,
    )
    monkeypatch.setattr(alvo, "iniciar", iniciar_falhando)
    monkeypatch.setattr(modulo, "ESPERA_RECONEXAO_SEGUNDOS", 0.01)

    async def cenario():
        encerramento = asyncio.Event()
        tarefa = asyncio.create_task(alvo.executar(encerramento))
        await asyncio.sleep(0.1)
        encerramento.set()
        await asyncio.wait_for(tarefa, 1)

    asyncio.run(cenario())

    assert len(tentativas) > 1


class _Requisicao:
    def __init__(self, resposta):
        self.resposta = resposta

    def execute(self):
        return self.resposta


class DriveFalso:
    def __init__(self, paginas):
        self.paginas = paginas
        self.pedidas = []

    def changes(self):
        return self

    def list(self, **parametros):
        self.pedidas.append(parametros)
        return _Requisicao(self.paginas[parametros["pageToken"]])


def test_mudancas_percorrem_todas_as_paginas_ate_o_cursor_novo():
    drive = DriveFalso(
        {
            "10": {"changes": [{"fileId": "a"}], "nextPageToken": "p2"},
            "p2": {"changes": [{"fileId": "b", "removed": True}], "newStartPageToken": "11"},
        }
    )
    sincronizacao = SincronizacaoDrive(lambda: drive, reindexar=None)
    sincronizacao._servico = drive

    arquivos, cursor = sincronizacao._listar_mudancas("10")

    assert (arquivos, cursor) == ({"a", "b"}, "11")
    assert [p["pageToken"] for p in drive.pedidas] == ["10", "p2"]
    assert all(p["includeRemoved"] and p["supportsAllDrives"] for p in drive.pedidas)


def test_listagem_sem_cursor_novo_e_um_erro():
    drive = DriveFalso({"10": {"changes": []}})
    sincronizacao = SincronizacaoDrive(lambda: drive, reindexar=None)
    sincronizacao._servico = drive

    with pytest.raises(RuntimeError):
        sincronizacao._listar_mudancas("10")
