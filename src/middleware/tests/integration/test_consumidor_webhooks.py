"""Consumidor de webhooks contra PostgreSQL e RabbitMQ reais.

Cobre os três casos do DoD da #394 — sucesso, falha transitória e falha
definitiva — e os dois tratadores: a aplicação dos eventos do portfólio
com controle de versão (WH-02) e a sincronização do corpus a partir das
mudanças do Drive (WH-01, com a Drive API dublada). Os eventos entram na
fila como a rota os publica: um recebimento gravado e o envelope com o
mesmo `message_id`.

Cada teste usa um vhost descartável, uma fonte e entidades próprias, e
apaga o que gravou. Pula limpo sem banco ou sem broker.
"""

import asyncio
import uuid
from datetime import UTC, datetime
from urllib.parse import quote, unquote, urlsplit, urlunsplit

import aio_pika
import httpx
import pytest
from sqlalchemy import delete, inspect, select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.config import settings
from app.mensageria.consumidor import ConsumidorWebhooks, FalhaDefinitiva
from app.mensageria.produtor import ProdutorEventos
from app.mensageria.topologia import FILA_FALHAS, declarar_topologia
from app.persistence.sessao import criar_engine
from app.persistence.tabelas_portfolio import ProjetoTabela, RiscoTabela
from app.webhooks.drive.recebimento import publicar_recebimento
from app.webhooks.drive.sincronizacao import SincronizacaoDrive
from app.webhooks.modelos import Provedor, TipoEventoPortfolio
from app.webhooks.portfolio.aplicacao import tratar_evento_portfolio
from app.webhooks.repositorio import (
    FontePortfolioRepository,
    RecebimentoRepository,
    SincronizacaoRepository,
)
from app.webhooks.tabelas import (
    AuditoriaPortfolioTabela,
    FontePortfolioTabela,
    RecebimentoTabela,
    SincronizacaoFonteTabela,
    VersaoEntidadeTabela,
)

pytestmark = pytest.mark.integracao

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
async def ambiente(fabrica, url_isolada):
    """Produtor, fonte descartável e um consumidor que o teste monta."""
    fonte = f"teste_{uuid.uuid4().hex[:8]}"
    produtor = ProdutorEventos(url_isolada, "prata.events", "prata.dead-letter")
    consumidores: list[ConsumidorWebhooks] = []

    async def consumir(tratadores, *, max_retries=2):
        alvo = ConsumidorWebhooks(
            url_isolada,
            exchange="prata.events",
            dead_letter_exchange="prata.dead-letter",
            fabrica=fabrica,
            tratadores=tratadores,
            max_retries=max_retries,
            prefetch=5,
        )
        await alvo.iniciar()
        consumidores.append(alvo)
        return alvo

    async def publicar(provider, evento, *, numero=None):
        chave = f"{fonte}:{numero or uuid.uuid4().hex}"
        async with fabrica() as sessao:
            recebimento, _ = await RecebimentoRepository(sessao).registrar(
                provedor=Provedor.GOOGLE_DRIVE,
                chave_externa=chave,
                fonte_id=fonte,
                canal_id=None,
                evento={"provider": provider, **evento},
                agora=datetime.now(UTC),
            )
            await sessao.commit()
        await publicar_recebimento(recebimento, fabrica=fabrica, produtor=produtor)
        return recebimento

    ambiente = type("Ambiente", (), {})()
    ambiente.fonte, ambiente.consumir, ambiente.publicar = fonte, consumir, publicar
    ambiente.produtor, ambiente.url = produtor, url_isolada
    yield ambiente
    for alvo in consumidores:
        await alvo.encerrar()
    await produtor.encerrar()
    async with fabrica() as sessao:
        await sessao.execute(delete(RecebimentoTabela).where(RecebimentoTabela.fonte_id == fonte))
        await sessao.execute(
            delete(SincronizacaoFonteTabela).where(SincronizacaoFonteTabela.fonte_id == fonte)
        )
        await sessao.commit()


async def estado(fabrica, recebimento):
    async with fabrica() as sessao:
        registro = await sessao.get(RecebimentoTabela, recebimento.message_id)
        return registro.processado_em is not None, registro.tentativas, registro.erro_codigo


async def descartados(url: str) -> list[str]:
    conexao = await aio_pika.connect(url)
    async with conexao:
        canal = await conexao.channel()
        await declarar_topologia(canal, "prata.events", "prata.dead-letter")
        fila = await canal.declare_queue(FILA_FALHAS, passive=True)
        lidas = []
        while (mensagem := await fila.get(fail=False)) is not None:
            lidas.append(mensagem.message_id)
            await mensagem.ack()
        return lidas


async def ate(condicao, prazo=10.0):
    fim = asyncio.get_running_loop().time() + prazo
    while asyncio.get_running_loop().time() < fim:
        if await condicao():
            return True
        await asyncio.sleep(0.2)
    return False


# --- Decisões do consumidor --------------------------------------------------


async def test_sucesso_processa_uma_vez_mesmo_com_reentrega(ambiente, fabrica):
    chamadas = []

    async def tratador(evento, sessao):
        chamadas.append(evento.message_id)

    await ambiente.consumir({"teste": tratador})
    recebimento = await ambiente.publicar("teste", {})
    assert await ate(lambda: _processado(fabrica, recebimento))

    await publicar_recebimento(recebimento, fabrica=fabrica, produtor=ambiente.produtor)
    await asyncio.sleep(1)

    assert len(chamadas) == 1
    assert await estado(fabrica, recebimento) == (True, 0, None)


async def _processado(fabrica, recebimento):
    return (await estado(fabrica, recebimento))[0]


async def test_falha_definitiva_vai_para_a_fila_de_falhas(ambiente, fabrica):
    async def tratador(evento, sessao):
        raise FalhaDefinitiva("CONFLITO_DE_VERSAO")

    await ambiente.consumir({"teste": tratador})
    recebimento = await ambiente.publicar("teste", {})
    await asyncio.sleep(1)

    assert await descartados(ambiente.url) == [recebimento.message_id]
    assert await estado(fabrica, recebimento) == (False, 1, "CONFLITO_DE_VERSAO")


async def test_provedor_sem_tratador_e_descartado(ambiente, fabrica):
    await ambiente.consumir({})
    recebimento = await ambiente.publicar("desconhecido", {})
    await asyncio.sleep(1)

    assert await descartados(ambiente.url) == [recebimento.message_id]
    assert (await estado(fabrica, recebimento))[2] == "PROVEDOR_SEM_TRATADOR"


async def test_falha_transitoria_espera_e_tenta_de_novo_ate_esgotar(ambiente, fabrica):
    instantes = []

    async def tratador(evento, sessao):
        instantes.append(asyncio.get_running_loop().time())
        raise ConnectionError("serviço fora")

    await ambiente.consumir({"teste": tratador}, max_retries=1)
    recebimento = await ambiente.publicar("teste", {})

    assert await ate(lambda: _descartou(ambiente.url, recebimento), prazo=15)
    assert len(instantes) == 2
    assert instantes[1] - instantes[0] >= 4.5  # primeira espera: 5 s
    assert await estado(fabrica, recebimento) == (False, 2, "PROCESSAMENTO_TRANSITORIO")


async def _descartou(url, recebimento):
    return recebimento.message_id in await descartados(url)


async def test_falha_transitoria_seguida_de_sucesso(ambiente, fabrica):
    tentativas = []

    async def tratador(evento, sessao):
        tentativas.append(1)
        if len(tentativas) == 1:
            raise ConnectionError("serviço fora")

    await ambiente.consumir({"teste": tratador})
    recebimento = await ambiente.publicar("teste", {})

    assert await ate(lambda: _processado(fabrica, recebimento), prazo=15)
    assert len(tentativas) == 2


# --- WH-02: aplicação no portfólio -------------------------------------------


@pytest.fixture
async def risco(fabrica, ambiente):
    projeto = f"teste-{uuid.uuid4().hex[:8]}"
    identificador = f"{projeto}-risco"
    agora = datetime.now(UTC)
    async with fabrica() as sessao:
        sessao.add(
            ProjetoTabela(
                codigo=projeto,
                nome=projeto,
                status="em_andamento",
                prioridade="media",
                avanco_percentual=10,
                criado_em=agora,
                atualizado_em=agora,
            )
        )
        await sessao.flush()
        sessao.add(
            RiscoTabela(
                id=identificador,
                projeto_codigo=projeto,
                descricao="risco sintético",
                probabilidade=3,
                impacto=4,
                status="monitorado",
                criado_em=agora,
                atualizado_em=agora,
            )
        )
        await FontePortfolioRepository(sessao).salvar(
            source_id=ambiente.fonte,
            planilha_id="planilha",
            projetos={projeto},
            tipos={TipoEventoPortfolio.RISCO},
            agora=agora,
        )
        await sessao.commit()
    yield projeto, identificador
    async with fabrica() as sessao:
        for tabela in (AuditoriaPortfolioTabela, VersaoEntidadeTabela):
            await sessao.execute(delete(tabela).where(tabela.source_id == ambiente.fonte))
        await sessao.execute(
            delete(FontePortfolioTabela).where(FontePortfolioTabela.source_id == ambiente.fonte)
        )
        await sessao.execute(delete(RiscoTabela).where(RiscoTabela.id == identificador))
        await sessao.execute(delete(ProjetoTabela).where(ProjetoTabela.codigo == projeto))
        await sessao.commit()


def evento_de_risco(fonte, projeto, identificador, versao, **dados):
    campos = {"status": "monitorado", "probabilidade": 3, "impacto": 4}
    campos.update(dados)
    return {
        "event": {
            "schema_version": 1,
            "event_id": str(uuid.uuid4()),
            "source_id": fonte,
            "event_type": "risco.alterado",
            "occurred_at": "2026-09-24T12:00:00Z",
            "projeto_codigo": projeto,
            "entity_id": identificador,
            "version": versao,
            "data": campos,
        }
    }


async def valores_do_risco(fabrica, identificador):
    async with fabrica() as sessao:
        registro = await sessao.get(RiscoTabela, identificador)
        return registro.status, registro.probabilidade, registro.impacto


async def resultados(fabrica, fonte):
    async with fabrica() as sessao:
        linhas = await sessao.scalars(
            select(AuditoriaPortfolioTabela)
            .where(AuditoriaPortfolioTabela.source_id == fonte)
            .order_by(AuditoriaPortfolioTabela.registrado_em)
        )
        return [(linha.versao, linha.resultado) for linha in linhas]


async def test_versoes_do_portfolio_seguem_o_contrato(ambiente, fabrica, risco):
    projeto, identificador = risco
    await ambiente.consumir({"apps_script": tratar_evento_portfolio})

    async def enviar(versao, **dados):
        evento = evento_de_risco(ambiente.fonte, projeto, identificador, versao, **dados)
        recebimento = await ambiente.publicar("apps_script", evento)
        await asyncio.sleep(0.7)
        return recebimento

    await enviar(2, probabilidade=5)
    assert await valores_do_risco(fabrica, identificador) == ("monitorado", 5, 4)
    await enviar(1, probabilidade=1)  # antiga
    await enviar(2, probabilidade=5)  # mesma versão, mesmos dados
    await enviar(3, probabilidade=5)  # nova versão sem diferença
    conflito = await enviar(3, probabilidade=2)  # mesma versão, outros dados
    await enviar(7, status="mitigado", probabilidade=2, impacto=2)  # lacuna

    assert await valores_do_risco(fabrica, identificador) == ("mitigado", 2, 2)
    assert await descartados(ambiente.url) == [conflito.message_id]
    assert await resultados(fabrica, ambiente.fonte) == [
        (2, "aplicado"),
        (1, "ignorado_antigo"),
        (2, "repetido"),
        (3, "sem_diferenca"),
        (7, "aplicado"),
    ]


async def test_escopo_revogado_antes_do_processamento_nao_altera_dados(ambiente, fabrica, risco):
    projeto, identificador = risco
    async with fabrica() as sessao:
        await FontePortfolioRepository(sessao).salvar(
            source_id=ambiente.fonte,
            planilha_id="planilha",
            projetos={projeto},
            tipos={TipoEventoPortfolio.RISCO},
            ativa=False,
            agora=datetime.now(UTC),
        )
        await sessao.commit()
    await ambiente.consumir({"apps_script": tratar_evento_portfolio})

    recebimento = await ambiente.publicar(
        "apps_script", evento_de_risco(ambiente.fonte, projeto, identificador, 5, status="mitigado")
    )
    await asyncio.sleep(1)

    assert await valores_do_risco(fabrica, identificador) == ("monitorado", 3, 4)
    assert await descartados(ambiente.url) == [recebimento.message_id]
    assert (await estado(fabrica, recebimento))[2] == "ESCOPO_REVOGADO"


# --- WH-01: sincronização do corpus ------------------------------------------


class _Requisicao:
    def __init__(self, resposta):
        self.resposta = resposta

    def execute(self):
        return self.resposta


class DriveFalso:
    def __init__(self):
        self.paginas = {
            "100": {"changes": [{"fileId": "a"}], "nextPageToken": "p2"},
            "p2": {"changes": [{"fileId": "b", "removed": True}], "newStartPageToken": "101"},
            "101": {"changes": [], "newStartPageToken": "101"},
        }

    def changes(self):
        return self

    def list(self, **parametros):
        return _Requisicao(self.paginas[parametros["pageToken"]])


async def cursor(fabrica, fonte):
    async with fabrica() as sessao:
        return await SincronizacaoRepository(sessao).obter_cursor(fonte)


async def test_mudancas_do_drive_reindexam_e_avancam_o_cursor(ambiente, fabrica):
    async with fabrica() as sessao:
        await SincronizacaoRepository(sessao).salvar_cursor(
            ambiente.fonte, "100", agora=datetime.now(UTC)
        )
        await sessao.commit()
    reindexacoes = []

    async def reindexar():
        reindexacoes.append(1)

    sincronizacao = SincronizacaoDrive(DriveFalso, reindexar=reindexar)
    await ambiente.consumir({"google_drive": sincronizacao.tratar})

    primeiro = await ambiente.publicar("google_drive", {"fonte_id": ambiente.fonte})
    assert await ate(lambda: _processado(fabrica, primeiro))
    segundo = await ambiente.publicar("google_drive", {"fonte_id": ambiente.fonte})
    assert await ate(lambda: _processado(fabrica, segundo))

    assert reindexacoes == [1]  # a segunda notificação não trouxe mudança nova
    assert await cursor(fabrica, ambiente.fonte) == "101"


async def test_reindexacao_que_falha_preserva_o_cursor(ambiente, fabrica):
    async with fabrica() as sessao:
        await SincronizacaoRepository(sessao).salvar_cursor(
            ambiente.fonte, "100", agora=datetime.now(UTC)
        )
        await sessao.commit()

    async def reindexar():
        raise ConnectionError("índice fora")

    sincronizacao = SincronizacaoDrive(DriveFalso, reindexar=reindexar)
    await ambiente.consumir({"google_drive": sincronizacao.tratar}, max_retries=0)

    recebimento = await ambiente.publicar("google_drive", {"fonte_id": ambiente.fonte})
    await asyncio.sleep(1)

    assert await cursor(fabrica, ambiente.fonte) == "100"
    assert await descartados(ambiente.url) == [recebimento.message_id]


async def test_fonte_sem_cursor_e_falha_definitiva(ambiente, fabrica):
    sincronizacao = SincronizacaoDrive(DriveFalso, reindexar=None)
    await ambiente.consumir({"google_drive": sincronizacao.tratar})

    recebimento = await ambiente.publicar("google_drive", {"fonte_id": ambiente.fonte})
    await asyncio.sleep(1)

    assert (await estado(fabrica, recebimento))[2] == "CURSOR_AUSENTE"
