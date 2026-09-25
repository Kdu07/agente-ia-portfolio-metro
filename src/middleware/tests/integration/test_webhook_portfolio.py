"""WH-02 contra PostgreSQL e RabbitMQ reais.

Da assinatura até a fila: o cadastro de chaves relido a cada entrega, o
escopo da fonte no banco, o vínculo da entidade com o projeto, o hash do
corpo decidindo entre 204 e 409 e a recuperação de pendentes do worker
cobrindo também este webhook. As requisições são assinadas como o
emissor assina (src/emissor-portfolio/Codigo.gs).

Cada teste cria o próprio projeto, risco e marco, uma fonte e um vhost
descartáveis, e apaga o que gravou. Pula limpo sem banco ou sem broker.
"""

import asyncio
import base64
import hashlib
import hmac
import json
import secrets
import time
import uuid
from datetime import UTC, date, datetime, timedelta
from urllib.parse import quote, unquote, urlsplit, urlunsplit

import aio_pika
import httpx
import pytest
from sqlalchemy import delete, inspect, select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.api import deps
from app.config import settings
from app.main import app
from app.mensageria.consumidor import ConsumidorWebhooks
from app.mensageria.produtor import ProdutorEventos
from app.mensageria.topologia import WEBHOOK_RECEBIDO, declarar_topologia
from app.persistence.sessao import criar_engine
from app.persistence.tabelas_portfolio import MarcoTabela, ProjetoTabela, RiscoTabela
from app.webhooks.drive.manutencao import republicar_pendentes
from app.webhooks.modelos import TipoEventoPortfolio
from app.webhooks.portfolio.aplicacao import tratar_evento_portfolio
from app.webhooks.repositorio import FontePortfolioRepository, RecebimentoRepository
from app.webhooks.tabelas import (
    AuditoriaPortfolioTabela,
    FontePortfolioTabela,
    RecebimentoTabela,
    VersaoEntidadeTabela,
)

pytestmark = pytest.mark.integracao

ROTA = "/webhooks/portfolio"
PORTA_GERENCIAMENTO = 15672


@pytest.fixture
async def fabrica():
    engine = criar_engine()
    try:
        async with engine.connect() as conexao:
            esquemas = await conexao.run_sync(lambda s: inspect(s).get_schema_names())
    except Exception:  # noqa: BLE001 — qualquer falha de conexão pula a suíte
        await engine.dispose()
        pytest.skip("PostgreSQL indisponível.")
    if not {"webhook", "portfolio"} <= set(esquemas):
        await engine.dispose()
        pytest.skip("Schemas ausentes. Rode `alembic upgrade head`.")
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


@pytest.fixture
async def portfolio(fabrica):
    """Dois projetos com um risco e um marco cada, criados só para o teste."""
    sufixo = uuid.uuid4().hex[:8]
    agora = datetime.now(UTC)
    codigos = [f"teste-{sufixo}-a", f"teste-{sufixo}-b"]
    async with fabrica() as sessao:
        for codigo in codigos:
            sessao.add(
                ProjetoTabela(
                    codigo=codigo,
                    nome=codigo,
                    status="em_andamento",
                    prioridade="media",
                    avanco_percentual=10,
                    criado_em=agora,
                    atualizado_em=agora,
                )
            )
        await sessao.flush()
        for codigo in codigos:
            sessao.add(
                RiscoTabela(
                    id=f"{codigo}-risco",
                    projeto_codigo=codigo,
                    descricao="risco sintético",
                    probabilidade=3,
                    impacto=4,
                    status="monitorado",
                    criado_em=agora,
                    atualizado_em=agora,
                )
            )
            sessao.add(
                MarcoTabela(
                    id=f"{codigo}-marco",
                    projeto_codigo=codigo,
                    nome="marco sintético",
                    data_prevista=date(2026, 10, 1),
                    status="em_andamento",
                    criado_em=agora,
                    atualizado_em=agora,
                )
            )
        await sessao.commit()
    yield codigos
    async with fabrica() as sessao:
        for tabela in (RiscoTabela, MarcoTabela):
            await sessao.execute(delete(tabela).where(tabela.projeto_codigo.in_(codigos)))
        await sessao.execute(delete(ProjetoTabela).where(ProjetoTabela.codigo.in_(codigos)))
        await sessao.commit()


@pytest.fixture
async def url_isolada():
    url = urlsplit(settings.rabbitmq_url.get_secret_value())
    usuario, senha = unquote(url.username or ""), unquote(url.password or "")
    vhost = f"prata-teste-{uuid.uuid4().hex[:10]}"
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


class Emissor:
    """Assina como o Codigo.gs: HMAC-SHA256 sobre o prefixo e o corpo exato."""

    def __init__(self, fonte: str, segredo: bytes, projeto: str) -> None:
        self.fonte, self.segredo, self.projeto = fonte, segredo, projeto

    def evento(self, **mudancas) -> dict:
        corpo = {
            "schema_version": 1,
            "event_id": str(uuid.uuid4()),
            "source_id": self.fonte,
            "event_type": "risco.alterado",
            "occurred_at": "2026-09-24T12:00:00Z",
            "projeto_codigo": self.projeto,
            "entity_id": f"{self.projeto}-risco",
            "version": 1,
            "data": {"status": "mitigado", "probabilidade": 2, "impacto": 4},
        }
        corpo.update(mudancas)
        return corpo

    def cabecalhos(self, corpo: bytes, *, timestamp: int | None = None) -> dict[str, str]:
        instante = str(int(time.time()) if timestamp is None else timestamp)
        entrada = f"{self.fonte}\nk1\n{instante}\n".encode() + corpo
        assinatura = base64.b64encode(hmac.digest(self.segredo, entrada, hashlib.sha256))
        return {
            "Content-Type": "application/json",
            "X-Prata-Source": self.fonte,
            "X-Prata-Key-Id": "k1",
            "X-Prata-Timestamp": instante,
            "X-Prata-Signature": assinatura.decode(),
        }


@pytest.fixture
async def emissor(fabrica, portfolio, tmp_path, monkeypatch):
    fonte = f"teste_{uuid.uuid4().hex[:8]}"
    segredo = secrets.token_bytes(32)
    arquivo = tmp_path / "chaves.json"
    arquivo.write_text(
        json.dumps(
            [
                {
                    "source_id": fonte,
                    "key_id": "k1",
                    "segredo_base64": base64.b64encode(segredo).decode(),
                    "valida_desde": 0,
                    "valida_ate": 4102444800,
                    "revogada": False,
                }
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(settings, "webhook_portfolio_chaves_arquivo", str(arquivo))
    async with fabrica() as sessao:
        await FontePortfolioRepository(sessao).salvar(
            source_id=fonte,
            planilha_id="planilha-teste",
            projetos={portfolio[0]},
            tipos={TipoEventoPortfolio.RISCO, TipoEventoPortfolio.MARCO},
            agora=datetime.now(UTC),
        )
        await sessao.commit()
    yield Emissor(fonte, segredo, portfolio[0])
    async with fabrica() as sessao:
        for tabela in (AuditoriaPortfolioTabela, VersaoEntidadeTabela):
            await sessao.execute(delete(tabela).where(tabela.source_id == fonte))
        await sessao.execute(delete(RecebimentoTabela).where(RecebimentoTabela.fonte_id == fonte))
        await sessao.execute(
            delete(FontePortfolioTabela).where(FontePortfolioTabela.source_id == fonte)
        )
        await sessao.commit()


@pytest.fixture
async def cliente(fabrica, produtor, emissor, monkeypatch):
    monkeypatch.setitem(app.dependency_overrides, deps.obter_produtor, lambda: produtor)
    monkeypatch.setitem(app.dependency_overrides, deps.obter_fabrica_sessoes, lambda: fabrica)
    transporte = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transporte, base_url="http://teste") as c:
        yield c


def _bytes(evento: dict) -> bytes:
    return json.dumps(evento, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


async def enviar(cliente, emissor, evento=None, *, corpo=None, **opcoes):
    corpo = _bytes(evento) if corpo is None else corpo
    cabecalhos = emissor.cabecalhos(corpo, timestamp=opcoes.pop("timestamp", None))
    cabecalhos.update(opcoes.pop("cabecalhos", {}))
    return await cliente.post(ROTA, content=corpo, headers=cabecalhos)


async def fila(url: str) -> list[aio_pika.abc.AbstractIncomingMessage]:
    conexao = await aio_pika.connect(url)
    async with conexao:
        canal = await conexao.channel()
        await declarar_topologia(canal, "prata.events", "prata.dead-letter")
        destino = await canal.declare_queue(WEBHOOK_RECEBIDO.nome, passive=True)
        lidas = []
        await asyncio.sleep(0.2)
        while (mensagem := await destino.get(fail=False)) is not None:
            await mensagem.ack()
            lidas.append(mensagem)
        return lidas


async def test_evento_valido_chega_a_fila_com_o_evento_validado(
    cliente, emissor, fabrica, url_isolada
):
    evento = emissor.evento()

    resposta = await enviar(cliente, emissor, evento)

    assert resposta.status_code == 202
    [mensagem] = await fila(url_isolada)
    payload = json.loads(mensagem.body)["payload"]
    assert payload["provider"] == "apps_script"
    assert payload["event"]["event_id"] == evento["event_id"]
    async with fabrica() as sessao:
        registro = await sessao.get(RecebimentoTabela, mensagem.message_id)
    assert registro.chave_externa == f"{emissor.fonte}:{evento['event_id']}"
    assert bytes(registro.corpo_sha256) == hashlib.sha256(_bytes(evento)).digest()


async def test_mesmo_corpo_reenviado_responde_204(cliente, emissor, url_isolada):
    corpo = _bytes(emissor.evento())
    await enviar(cliente, emissor, corpo=corpo)

    repetido = await enviar(cliente, emissor, corpo=corpo)

    assert repetido.status_code == 204
    assert len(await fila(url_isolada)) == 1


async def test_mesmo_evento_com_outro_corpo_responde_409_e_preserva_o_original(
    cliente, emissor, fabrica, url_isolada
):
    evento = emissor.evento()
    await enviar(cliente, emissor, evento)

    conflito = await enviar(cliente, emissor, dict(evento, version=2))

    assert conflito.status_code == 409
    assert conflito.json()["detail"]["codigo"] == "WEBHOOK_EVENTO_CONFLITANTE"
    async with fabrica() as sessao:
        registros = await RecebimentoRepository(sessao).listar_pendentes(
            recebidos_antes=datetime.now(UTC) + timedelta(days=1)
        )
    assert registros == []  # o original segue publicado, sem novo pendente
    assert len(await fila(url_isolada)) == 1


async def test_marco_do_projeto_autorizado_e_aceito(cliente, emissor):
    evento = emissor.evento(
        event_type="marco.alterado",
        entity_id=f"{emissor.projeto}-marco",
        data={"status": "concluido", "data_prevista": "2026-10-01", "data_real": "2026-09-20"},
    )

    assert (await enviar(cliente, emissor, evento)).status_code == 202


async def test_entidade_de_outro_projeto_responde_422(cliente, emissor, portfolio):
    evento = emissor.evento(entity_id=f"{portfolio[1]}-risco")

    resposta = await enviar(cliente, emissor, evento)

    assert (resposta.status_code, resposta.json()["detail"]["codigo"]) == (
        422,
        "WEBHOOK_PAYLOAD_INVALIDO",
    )


async def test_projeto_fora_do_escopo_responde_403(cliente, emissor, portfolio):
    evento = emissor.evento(projeto_codigo=portfolio[1], entity_id=f"{portfolio[1]}-risco")

    assert (await enviar(cliente, emissor, evento)).status_code == 403


async def test_assinatura_fora_da_janela_responde_401(cliente, emissor, fabrica):
    resposta = await enviar(cliente, emissor, emissor.evento(), timestamp=int(time.time()) - 600)

    assert resposta.status_code == 401
    async with fabrica() as sessao:
        assert (
            await RecebimentoRepository(sessao).listar_pendentes(
                recebidos_antes=datetime.now(UTC) + timedelta(days=1)
            )
            == []
        )


async def test_assinatura_hmac_incorreta_responde_401_sem_publicar(
    cliente, emissor, fabrica, url_isolada
):
    corpo = _bytes(emissor.evento())
    cabecalhos = emissor.cabecalhos(corpo)
    cabecalhos["X-Prata-Signature"] = base64.b64encode(b"x" * 32).decode()

    resposta = await cliente.post(ROTA, content=corpo, headers=cabecalhos)

    assert resposta.status_code == 401
    async with fabrica() as sessao:
        assert (
            await RecebimentoRepository(sessao).listar_pendentes(
                recebidos_antes=datetime.now(UTC) + timedelta(days=1)
            )
            == []
        )
    assert await fila(url_isolada) == []


async def test_json_malformado_responde_400_sem_publicar(cliente, emissor, url_isolada):
    corpo = b'{"event_id":'

    resposta = await enviar(cliente, emissor, corpo=corpo)

    assert resposta.status_code == 400
    assert resposta.json()["detail"]["codigo"] == "WEBHOOK_INVALIDO"
    assert await fila(url_isolada) == []


async def test_conteudo_que_nao_e_json_responde_415(cliente, emissor):
    resposta = await enviar(
        cliente, emissor, emissor.evento(), cabecalhos={"Content-Type": "text/plain"}
    )

    assert resposta.status_code == 415


async def test_corpo_acima_de_32_kib_responde_413(cliente, emissor):
    resposta = await enviar(cliente, emissor, corpo=b" " * (33 * 1024))

    assert resposta.status_code == 413


async def test_cadastro_de_chaves_ilegivel_responde_503(cliente, emissor, monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "webhook_portfolio_chaves_arquivo", str(tmp_path / "nada.json"))

    resposta = await enviar(cliente, emissor, emissor.evento())

    assert resposta.status_code == 503
    assert resposta.headers["retry-after"] == "5"


async def test_broker_fora_deixa_pendente_que_o_worker_republica(
    cliente, emissor, fabrica, produtor, url_isolada, monkeypatch
):
    fora = ProdutorEventos(
        "amqp://ninguem:nada@127.0.0.1:1/x",
        "prata.events",
        "prata.dead-letter",
        timeout_segundos=1,
    )
    monkeypatch.setitem(app.dependency_overrides, deps.obter_produtor, lambda: fora)
    evento = emissor.evento()

    resposta = await enviar(cliente, emissor, evento)

    assert resposta.status_code == 503
    publicados = await republicar_pendentes(
        fabrica, produtor, relogio=lambda: datetime.now(UTC) + timedelta(minutes=1)
    )
    assert publicados == 1
    [mensagem] = await fila(url_isolada)
    assert json.loads(mensagem.body)["payload"]["event"]["event_id"] == evento["event_id"]


async def test_rota_publica_e_consumidor_aplica_evento_no_portfolio(
    cliente, emissor, fabrica, url_isolada
):
    consumidor = ConsumidorWebhooks(
        url_isolada,
        exchange="prata.events",
        dead_letter_exchange="prata.dead-letter",
        fabrica=fabrica,
        tratadores={"apps_script": tratar_evento_portfolio},
        max_retries=2,
        prefetch=1,
    )
    await consumidor.iniciar()
    evento = emissor.evento(
        version=7,
        data={"status": "materializado", "probabilidade": 5, "impacto": 5},
    )
    try:
        resposta = await enviar(cliente, emissor, evento)
        assert resposta.status_code == 202

        for _ in range(50):
            async with fabrica() as sessao:
                risco = await sessao.get(RiscoTabela, evento["entity_id"])
                recebimento = await sessao.scalar(
                    select(RecebimentoTabela).where(
                        RecebimentoTabela.chave_externa
                        == f"{emissor.fonte}:{evento['event_id']}"
                    )
                )
                if (
                    risco is not None
                    and recebimento is not None
                    and risco.status == "materializado"
                    and recebimento.processado_em is not None
                ):
                    break
            await asyncio.sleep(0.1)
        else:
            pytest.fail("O evento aceito pela rota não foi aplicado pelo consumidor")
    finally:
        await consumidor.encerrar()
