"""Lógica de recebimento do WH-01 com banco e broker dublados.

Os dublês permitem provocar cada ramo da seção 9.1.2.7.1 do Projeto.md
de forma determinística: canal pendente, repetição já publicada,
repetição pendente, broker sem confirmação, banco fora do ar e orçamento
de 3 segundos estourado. O ciclo contra PostgreSQL e RabbitMQ reais está
em tests/integration/test_webhook_drive.py.
"""

import asyncio
import dataclasses
import hashlib
import time
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from app.auth.webhooks import WebhookRecusado
from app.auth.webhooks_drive import CanalDrive
from app.mensageria.produtor import FalhaPublicacao
from app.webhooks.drive import recebimento as modulo
from app.webhooks.drive.recebimento import receber_notificacao
from app.webhooks.modelos import Recebimento

FONTE = "corpus_teste"
CANAL = str(uuid4())
TOKEN = "t" * 64
RECURSO = "recurso-confirmado"
URI = "https://www.googleapis.com/drive/v3/changes?pageToken=1"


def cabecalhos(estado="change", numero="680081", token=TOKEN, recurso=RECURSO):
    return [
        (b"x-goog-channel-id", CANAL.encode()),
        (b"x-goog-channel-token", token.encode()),
        (b"x-goog-resource-id", recurso.encode()),
        (b"x-goog-resource-uri", URI.encode()),
        (b"x-goog-resource-state", estado.encode()),
        (b"x-goog-message-number", numero.encode()),
    ]


class Banco:
    """Estado compartilhado pelos repositórios dublados."""

    def __init__(self, *, pendente=False) -> None:
        self.canais = {
            CANAL: CanalDrive(
                fonte=FONTE,
                token_sha256=hashlib.sha256(TOKEN.encode()).digest(),
                expira_em=time.time() + 3600,
                recurso_id=None if pendente else RECURSO,
                recurso_uri=None if pendente else URI,
                pendente=pendente,
            )
        }
        self.recebimentos: dict[str, Recebimento] = {}
        self.falhas: list[str] = []
        self.commits = 0
        self.indisponivel = False


class Sessao:
    def __init__(self, banco: Banco) -> None:
        self.banco = banco

    async def __aenter__(self):
        if self.banco.indisponivel:
            raise OSError("conexão recusada")
        return self

    async def __aexit__(self, *erro):
        return False

    async def commit(self):
        self.banco.commits += 1


class Canais:
    def __init__(self, sessao: Sessao) -> None:
        self.banco = sessao.banco

    async def obter_para_verificacao(self, canal_id):
        return self.banco.canais.get(canal_id)


class Recebimentos:
    def __init__(self, sessao: Sessao) -> None:
        self.banco = sessao.banco

    async def registrar(self, *, provedor, chave_externa, fonte_id, canal_id, evento, agora):
        if chave_externa in self.banco.recebimentos:
            return self.banco.recebimentos[chave_externa], False
        novo = Recebimento(
            message_id=str(uuid4()),
            correlation_id=str(uuid4()),
            provedor=provedor,
            chave_externa=chave_externa,
            fonte_id=fonte_id,
            canal_id=canal_id,
            evento=evento,
            recebido_em=agora,
            publicado_em=None,
            processado_em=None,
            tentativas=0,
            erro_codigo=None,
        )
        self.banco.recebimentos[chave_externa] = novo
        return novo, True

    def _trocar(self, message_id, **campos):
        for chave, registro in self.banco.recebimentos.items():
            if registro.message_id == message_id:
                self.banco.recebimentos[chave] = dataclasses.replace(registro, **campos)

    async def marcar_publicado(self, message_id, *, agora):
        self._trocar(message_id, publicado_em=agora)

    async def registrar_falha(self, message_id, *, codigo):
        self.banco.falhas.append(codigo)


class Produtor:
    def __init__(self, *, erro=None, atraso=0.0) -> None:
        self.erro, self.atraso, self.publicados = erro, atraso, []

    async def publicar(self, evento):
        await asyncio.sleep(self.atraso)
        if self.erro is not None:
            raise self.erro
        self.publicados.append(evento)


@pytest.fixture
def banco(monkeypatch):
    monkeypatch.setattr(modulo, "CanalDriveRepository", Canais)
    monkeypatch.setattr(modulo, "RecebimentoRepository", Recebimentos)
    return Banco()


async def receber(banco, produtor, cab=None, corpo=b""):
    return await receber_notificacao(
        cabecalhos() if cab is None else cab,
        corpo,
        fabrica=lambda: Sessao(banco),
        produtor=produtor,
        fonte_id=FONTE,
    )


async def test_mudanca_valida_registra_publica_e_responde_202(banco):
    produtor = Produtor()

    assert await receber(banco, produtor) == 202

    [registro] = banco.recebimentos.values()
    [evento] = produtor.publicados
    assert registro.chave_externa == f"{CANAL}:680081"
    assert registro.publicado_em is not None
    assert (evento.message_id, evento.correlation_id) == (
        UUID(registro.message_id),
        UUID(registro.correlation_id),
    )
    assert evento.event_type == "webhook.received"
    assert evento.payload == {
        "provider": "google_drive",
        "fonte_id": FONTE,
        "channel_id": CANAL,
        "resource_id": RECURSO,
        "resource_state": "change",
        "message_number": "680081",
    }


async def test_evento_nao_carrega_token_nem_uri(banco):
    produtor = Produtor()

    await receber(banco, produtor)

    serializado = produtor.publicados[0].model_dump_json()
    assert TOKEN not in serializado
    assert "googleapis" not in serializado


async def test_sync_responde_204_sem_registrar_nem_publicar(banco):
    produtor = Produtor()

    assert await receber(banco, produtor, cabecalhos("sync", "1")) == 204

    assert banco.recebimentos == {}
    assert produtor.publicados == []


async def test_estado_nao_suportado_e_ignorado_com_204(banco):
    produtor = Produtor()

    assert await receber(banco, produtor, cabecalhos("trash")) == 204

    assert banco.recebimentos == {}


async def test_grafia_changed_do_exemplo_oficial_e_normalizada(banco):
    produtor = Produtor()

    assert await receber(banco, produtor, cabecalhos("changed")) == 202

    assert produtor.publicados[0].payload["resource_state"] == "change"


async def test_repeticao_ja_publicada_responde_204_sem_publicar_de_novo(banco):
    produtor = Produtor()
    await receber(banco, produtor)

    assert await receber(banco, produtor) == 204

    assert len(produtor.publicados) == 1
    assert len(banco.recebimentos) == 1


async def test_repeticao_pendente_publica_com_os_mesmos_identificadores(banco):
    falha = Produtor()
    falha.publicar = _falhar_publicacao
    with pytest.raises(WebhookRecusado):
        await receber(banco, falha)
    [pendente] = banco.recebimentos.values()
    assert pendente.publicado_em is None

    produtor = Produtor()
    assert await receber(banco, produtor) == 202

    assert produtor.publicados[0].message_id == UUID(pendente.message_id)


async def test_numeros_fora_de_ordem_sao_recebimentos_distintos(banco):
    produtor = Produtor()
    # Números observados numa única renomeação no teste com o Google real.
    for numero in ("686049", "680081", "759654"):
        assert await receber(banco, produtor, cabecalhos(numero=numero)) == 202

    assert len({evento.message_id for evento in produtor.publicados}) == 3


async def test_sem_confirmacao_do_broker_responde_503_e_conta_a_falha(banco):
    produtor = Produtor()
    produtor.publicar = _falhar_publicacao

    with pytest.raises(WebhookRecusado) as recusa:
        await receber(banco, produtor)

    assert (recusa.value.status, recusa.value.codigo) == (503, "WEBHOOK_INDISPONIVEL")
    assert banco.falhas == ["PUBLICACAO_NAO_CONFIRMADA"]
    [pendente] = banco.recebimentos.values()
    assert pendente.publicado_em is None


async def _falhar_publicacao(evento):
    raise FalhaPublicacao(evento, "DeliveryError")


@pytest.mark.parametrize(
    "cab,status",
    [
        (cabecalhos(token="x" * 64), 401),
        (cabecalhos(recurso="outro-recurso"), 401),
        ([c for c in cabecalhos() if c[0] != b"x-goog-message-number"], 400),
        ([c for c in cabecalhos() if c[0] != b"x-goog-channel-token"], 401),
    ],
)
async def test_recusa_autenticacao_antes_de_registrar(banco, cab, status):
    produtor = Produtor()

    with pytest.raises(WebhookRecusado) as recusa:
        await receber(banco, produtor, cab)

    assert recusa.value.status == status
    assert banco.recebimentos == {}
    assert produtor.publicados == []


async def test_canal_desconhecido_e_recusado(banco):
    banco.canais.clear()

    with pytest.raises(WebhookRecusado) as recusa:
        await receber(banco, Produtor())

    assert recusa.value.status == 401


async def test_corpo_nao_vazio_e_recusado(banco):
    with pytest.raises(WebhookRecusado) as recusa:
        await receber(banco, Produtor(), corpo=b"{}")

    assert recusa.value.status == 400


async def test_canal_pendente_aceita_sync_e_adia_mudanca(monkeypatch):
    monkeypatch.setattr(modulo, "CanalDriveRepository", Canais)
    monkeypatch.setattr(modulo, "RecebimentoRepository", Recebimentos)
    banco = Banco(pendente=True)

    assert await receber(banco, Produtor(), cabecalhos("sync", "1")) == 204
    with pytest.raises(WebhookRecusado) as recusa:
        await receber(banco, Produtor())

    assert recusa.value.status == 503


async def test_banco_indisponivel_responde_503(banco):
    banco.indisponivel = True

    with pytest.raises(WebhookRecusado) as recusa:
        await receber(banco, Produtor())

    assert (recusa.value.status, recusa.value.codigo) == (503, "WEBHOOK_INDISPONIVEL")


async def test_orcamento_de_tempo_estourado_responde_503(banco, monkeypatch):
    monkeypatch.setattr(modulo, "ORCAMENTO_SEGUNDOS", 0.05)

    with pytest.raises(WebhookRecusado) as recusa:
        await receber(banco, Produtor(atraso=1.0))

    assert recusa.value.status == 503


def test_evento_interno_usa_o_recebimento_como_origem():
    agora = datetime.now(UTC)
    registro = Recebimento(
        message_id=str(uuid4()),
        correlation_id=str(uuid4()),
        provedor=modulo.Provedor.GOOGLE_DRIVE,
        chave_externa="c:1",
        fonte_id=FONTE,
        canal_id=CANAL,
        evento={"provider": "google_drive"},
        recebido_em=agora,
        publicado_em=None,
        processado_em=None,
        tentativas=0,
        erro_codigo=None,
    )

    evento = modulo.evento_interno(registro)

    assert evento.occurred_at == agora
    assert (evento.producer, evento.schema_version) == ("middleware", 1)
