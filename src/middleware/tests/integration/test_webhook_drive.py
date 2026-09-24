"""WH-01 contra PostgreSQL e RabbitMQ reais, com o Google dublado.

O que está em dúvida aqui é a costura: a inscrição gravando o hash do
token que foi ao Google, a rota registrando no banco e publicando no
broker com os mesmos UUIDs, a repetição sem efeito duplicado, a
recuperação de pendentes depois de uma queda do broker e a renovação de
canal preservando a autenticação.

Só a Drive API é dublada: o teste com o Google real foi feito uma vez,
por túnel, e a estrutura observada está nos casos da suíte unitária.
Cada teste usa uma fonte própria e um vhost descartável, e apaga o que
gravou. Pula limpo sem banco ou sem broker. Para rodar:

    docker compose -f infra/docker-compose.yml up -d db rabbitmq
    alembic upgrade head
"""

import asyncio
import hashlib
import json
from datetime import UTC, datetime, timedelta
from urllib.parse import quote, unquote, urlsplit, urlunsplit
from uuid import uuid4

import aio_pika
import httpx
import pytest
from sqlalchemy import delete, inspect, update
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.api import deps
from app.config import settings
from app.main import app
from app.mensageria.produtor import ProdutorEventos
from app.mensageria.topologia import WEBHOOK_RECEBIDO, declarar_topologia
from app.persistence.sessao import criar_engine
from app.webhooks.drive.inscricao import ErroInscricao, InscricaoDrive
from app.webhooks.drive.manutencao import (
    executar_manutencao,
    renovar_canais,
    republicar_pendentes,
)
from app.webhooks.modelos import EstadoCanal
from app.webhooks.repositorio import (
    CanalDriveRepository,
    RecebimentoRepository,
    SincronizacaoRepository,
)
from app.webhooks.tabelas import CanalDriveTabela, RecebimentoTabela, SincronizacaoFonteTabela

pytestmark = pytest.mark.integracao

URL_PUBLICA = "https://tunel.exemplo/webhooks/google-drive"
PORTA_GERENCIAMENTO = 15672


class _Requisicao:
    def __init__(self, resposta) -> None:
        self._resposta = resposta

    def execute(self):
        return self._resposta()


class DriveFalso:
    """Drive API v3 dublada: guarda o que a inscrição enviou ao Google."""

    def __init__(self, *, falhar: bool = False, falhar_parada: bool = False) -> None:
        self.falhar = falhar
        self.falhar_parada = falhar_parada
        self.corpos: list[dict] = []
        self.parametros: list[dict] = []
        self.parados: list[dict] = []
        self.cursores_pedidos = 0

    def changes(self):
        return self

    def channels(self):
        return self

    def getStartPageToken(self, **_):
        self.cursores_pedidos += 1
        return _Requisicao(lambda: {"startPageToken": "4242"})

    def watch(self, *, body, **parametros):
        self.corpos.append(body)
        self.parametros.append(parametros)

        def responder():
            if self.falhar:
                raise RuntimeError("403 do Google")
            expira = datetime.now(UTC) + timedelta(hours=24)
            return {
                "id": body["id"],
                "resourceId": "recurso-do-google",
                "resourceUri": "https://www.googleapis.com/drive/v3/changes?pageToken=4242",
                "expiration": str(int(expira.timestamp() * 1000)),
            }

        return _Requisicao(responder)

    def stop(self, body):
        self.parados.append(body)

        def responder():
            if self.falhar_parada:
                raise RuntimeError("503 do Google")

        return _Requisicao(responder)


@pytest.fixture
async def fabrica():
    """Sessões num engine próprio do teste; apaga a fonte do teste no fim."""
    engine = criar_engine()
    try:
        async with engine.connect() as conexao:
            esquemas = await conexao.run_sync(lambda s: inspect(s).get_schema_names())
    except Exception:  # noqa: BLE001 — qualquer falha de conexão pula a suíte
        await engine.dispose()
        pytest.skip("PostgreSQL indisponível.")
    if "webhook" not in esquemas:
        await engine.dispose()
        pytest.skip("Schema `webhook` ausente. Rode `alembic upgrade head`.")

    fonte = f"teste-{uuid4().hex[:10]}"
    sessoes = async_sessionmaker(engine, expire_on_commit=False)
    sessoes.fonte = fonte  # type: ignore[attr-defined]
    try:
        yield sessoes
    finally:
        async with sessoes() as sessao:
            for tabela in (RecebimentoTabela, CanalDriveTabela, SincronizacaoFonteTabela):
                await sessao.execute(delete(tabela).where(tabela.fonte_id == fonte))
            await sessao.commit()
        await engine.dispose()


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
            pytest.skip("RabbitMQ indisponível.")
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
async def produtor(url_isolada):
    alvo = ProdutorEventos(url_isolada, "prata.events", "prata.dead-letter")
    yield alvo
    await alvo.encerrar()


@pytest.fixture
def drive():
    return DriveFalso()


@pytest.fixture
def inscricao(drive, fabrica):
    return InscricaoDrive(
        drive,
        fabrica,
        fonte_id=fabrica.fonte,
        url=URL_PUBLICA,
        validade=timedelta(hours=24),
    )


@pytest.fixture
async def canal(inscricao, drive):
    """Canal ativo e o token que a inscrição mandou ao Google."""
    inscrito = await inscricao.inscrever()
    return inscrito.canal_id, drive.corpos[-1]["token"]


@pytest.fixture
async def cliente(fabrica, produtor, monkeypatch):
    monkeypatch.setattr(settings, "drive_webhook_fonte", fabrica.fonte)
    monkeypatch.setitem(app.dependency_overrides, deps.obter_produtor, lambda: produtor)
    monkeypatch.setitem(app.dependency_overrides, deps.obter_fabrica_sessoes, lambda: fabrica)
    transporte = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transporte, base_url="http://teste") as c:
        yield c


def cabecalhos(canal_id, token, *, estado="change", numero="680081"):
    return {
        "X-Goog-Channel-ID": canal_id,
        "X-Goog-Channel-Token": token,
        "X-Goog-Resource-ID": "recurso-do-google",
        "X-Goog-Resource-URI": "https://www.googleapis.com/drive/v3/changes?pageToken=4242",
        "X-Goog-Resource-State": estado,
        "X-Goog-Message-Number": numero,
    }


async def mensagens_na_fila(url: str) -> list[aio_pika.abc.AbstractIncomingMessage]:
    conexao = await aio_pika.connect(url)
    async with conexao:
        canal_amqp = await conexao.channel()
        # Sem nenhuma publicação, a fila ainda não existe no vhost do teste.
        await declarar_topologia(canal_amqp, "prata.events", "prata.dead-letter")
        fila = await canal_amqp.declare_queue(WEBHOOK_RECEBIDO.nome, passive=True)
        lidas = []
        await asyncio.sleep(0.2)
        while (mensagem := await fila.get(fail=False)) is not None:
            await mensagem.ack()
            lidas.append(mensagem)
        return lidas


async def recebimentos(fabrica):
    async with fabrica() as sessao:
        return await RecebimentoRepository(sessao).listar_pendentes(
            recebidos_antes=datetime.now(UTC) + timedelta(days=1), limite=100
        )


# --- Inscrição -------------------------------------------------------------


async def test_inscricao_ativa_canal_e_guarda_so_o_hash_do_token(canal, fabrica, drive):
    canal_id, token = canal

    async with fabrica() as sessao:
        registrado = await CanalDriveRepository(sessao).obter(canal_id)
        verificacao = await CanalDriveRepository(sessao).obter_para_verificacao(canal_id)
        cursor = await SincronizacaoRepository(sessao).obter_cursor(fabrica.fonte)

    assert registrado.estado == EstadoCanal.ATIVO
    assert registrado.recurso_id == "recurso-do-google"
    assert verificacao.token_sha256 == hashlib.sha256(token.encode()).digest()
    assert cursor == "4242"
    assert drive.corpos[0]["address"] == URL_PUBLICA
    assert drive.parametros[0] == {
        "pageToken": "4242",
        "spaces": "drive",
        "includeRemoved": True,
        "supportsAllDrives": True,
        "includeItemsFromAllDrives": True,
    }


async def test_inscricao_recusada_pelo_google_encerra_o_canal_pendente(fabrica):
    drive = DriveFalso(falhar=True)
    inscricao = InscricaoDrive(
        drive, fabrica, fonte_id=fabrica.fonte, url=URL_PUBLICA, validade=timedelta(hours=1)
    )

    with pytest.raises(RuntimeError):
        await inscricao.inscrever()

    async with fabrica() as sessao:
        [registrado] = await CanalDriveRepository(sessao).listar(fabrica.fonte)
    assert registrado.estado == EstadoCanal.ENCERRADO


async def test_inscricao_exige_url_https(fabrica, drive):
    inscricao = InscricaoDrive(
        drive, fabrica, fonte_id=fabrica.fonte, url="http://sem-tls", validade=timedelta(hours=1)
    )

    with pytest.raises(ErroInscricao):
        await inscricao.inscrever()

    assert drive.corpos == []


async def test_encerrar_para_o_canal_no_google_sem_exigir_url(canal, fabrica, drive):
    canal_id, _ = canal
    sem_url = InscricaoDrive(
        drive, fabrica, fonte_id=fabrica.fonte, url="", validade=timedelta(hours=1)
    )

    await sem_url.encerrar(canal_id)

    assert drive.parados == [{"id": canal_id, "resourceId": "recurso-do-google"}]
    async with fabrica() as sessao:
        assert (await CanalDriveRepository(sessao).obter(canal_id)).estado == EstadoCanal.ENCERRADO


async def test_falha_ao_parar_canal_nao_permite_renovacao_repetida(canal, fabrica, drive):
    canal_id, _ = canal
    drive.falhar_parada = True
    com_falha = InscricaoDrive(
        drive,
        fabrica,
        fonte_id=fabrica.fonte,
        url=URL_PUBLICA,
        validade=timedelta(hours=1),
    )

    with pytest.raises(RuntimeError, match="503 do Google"):
        await com_falha.encerrar(canal_id)

    async with fabrica() as sessao:
        registrado = await CanalDriveRepository(sessao).obter(canal_id)
    assert registrado.estado == EstadoCanal.ENCERRADO
    assert await renovar_canais(com_falha, fabrica) == 0


# --- Rota até a fila ---------------------------------------------------------


async def test_mudanca_chega_a_fila_com_os_identificadores_do_banco(
    canal, cliente, fabrica, url_isolada
):
    canal_id, token = canal

    resposta = await cliente.post("/webhooks/google-drive", headers=cabecalhos(canal_id, token))

    assert resposta.status_code == 202
    [mensagem] = await mensagens_na_fila(url_isolada)
    async with fabrica() as sessao:
        registro = await sessao.get(RecebimentoTabela, mensagem.message_id)
    assert registro is not None and registro.publicado_em is not None
    assert mensagem.correlation_id == registro.correlation_id
    assert json.loads(mensagem.body)["payload"]["channel_id"] == canal_id


async def test_repeticao_nao_publica_de_novo(canal, cliente, url_isolada):
    canal_id, token = canal
    await cliente.post("/webhooks/google-drive", headers=cabecalhos(canal_id, token))

    repetida = await cliente.post("/webhooks/google-drive", headers=cabecalhos(canal_id, token))

    assert repetida.status_code == 204
    assert len(await mensagens_na_fila(url_isolada)) == 1


async def test_sync_e_token_errado_nao_geram_trabalho(canal, cliente, fabrica, url_isolada):
    canal_id, token = canal

    sync = await cliente.post(
        "/webhooks/google-drive", headers=cabecalhos(canal_id, token, estado="sync", numero="1")
    )
    errado = await cliente.post("/webhooks/google-drive", headers=cabecalhos(canal_id, "x" * 64))

    assert (sync.status_code, errado.status_code) == (204, 401)
    assert await recebimentos(fabrica) == []
    assert await mensagens_na_fila(url_isolada) == []


# --- Recuperação e renovação ---------------------------------------------


async def test_broker_fora_deixa_pendente_que_a_recuperacao_publica(
    canal, cliente, fabrica, produtor, url_isolada, monkeypatch
):
    canal_id, token = canal
    fora = ProdutorEventos(
        "amqp://ninguem:nada@127.0.0.1:1/x",
        "prata.events",
        "prata.dead-letter",
        timeout_segundos=1,
    )
    monkeypatch.setitem(app.dependency_overrides, deps.obter_produtor, lambda: fora)

    resposta = await cliente.post("/webhooks/google-drive", headers=cabecalhos(canal_id, token))

    assert resposta.status_code == 503
    assert resposta.headers["retry-after"] == "5"
    [pendente] = await recebimentos(fabrica)
    assert (pendente.tentativas, pendente.erro_codigo) == (1, "PUBLICACAO_NAO_CONFIRMADA")

    publicados = await republicar_pendentes(
        fabrica, produtor, relogio=lambda: datetime.now(UTC) + timedelta(minutes=1)
    )

    assert publicados == 1
    [mensagem] = await mensagens_na_fila(url_isolada)
    assert mensagem.message_id == pendente.message_id
    assert await recebimentos(fabrica) == []


async def test_pendente_recente_fica_para_o_proximo_ciclo(canal, cliente, fabrica, monkeypatch):
    canal_id, token = canal
    fora = ProdutorEventos(
        "amqp://ninguem:nada@127.0.0.1:1/x",
        "prata.events",
        "prata.dead-letter",
        timeout_segundos=1,
    )
    monkeypatch.setitem(app.dependency_overrides, deps.obter_produtor, lambda: fora)
    await cliente.post("/webhooks/google-drive", headers=cabecalhos(canal_id, token))

    assert await republicar_pendentes(fabrica, fora) == 0


async def test_renovacao_ativa_o_novo_antes_de_encerrar_o_antigo(canal, inscricao, fabrica, drive):
    antigo, _ = canal
    agora = datetime.now(UTC)
    async with fabrica() as sessao:
        await sessao.execute(
            update(CanalDriveTabela)
            .where(CanalDriveTabela.canal_id == antigo)
            .values(ativado_em=agora - timedelta(hours=20), expira_em=agora + timedelta(hours=4))
        )
        await sessao.commit()

    assert await renovar_canais(inscricao, fabrica) == 1

    async with fabrica() as sessao:
        canais = {
            c.canal_id: c.estado for c in await CanalDriveRepository(sessao).listar(fabrica.fonte)
        }
    [novo] = [canal_id for canal_id, estado in canais.items() if estado == EstadoCanal.ATIVO]
    assert canais[antigo] == EstadoCanal.ENCERRADO
    assert novo != antigo
    assert drive.parados == [{"id": antigo, "resourceId": "recurso-do-google"}]
    assert drive.cursores_pedidos == 1  # o cursor salvo foi reaproveitado


async def test_canal_recente_nao_e_renovado(canal, inscricao, fabrica):
    assert await renovar_canais(inscricao, fabrica) == 0


async def test_manutencao_roda_um_ciclo_e_para_no_encerramento(canal, fabrica, produtor):
    encerramento = asyncio.Event()
    ciclos = []

    def contar():
        ciclos.append(1)
        encerramento.set()
        return fabrica

    await asyncio.wait_for(
        executar_manutencao(
            encerramento,
            fabrica=contar,
            produtor=produtor,
            inscricao=lambda: None,
            intervalo_segundos=60,
        ),
        timeout=10,
    )

    assert ciclos == [1]
