"""Preferências e avisos do portfólio contra PostgreSQL e RabbitMQ reais.

Duas costuras: o consumidor aplicando um evento do WH-02 e gerando os
avisos na mesma transação, só para quem aderiu e ainda tem acesso; e as
rotas autenticadas, que enxergam só os avisos do dono, dos projetos que a
sessão autoriza agora e dos últimos 30 dias.

Cada teste cria os próprios usuários, projeto, risco e fonte, e apaga o que
gravou. Pula limpo sem banco ou sem broker.
"""

import asyncio
import uuid
from datetime import UTC, datetime, timedelta
from urllib.parse import quote, unquote, urlsplit, urlunsplit

import httpx
import pytest
from sqlalchemy import delete, inspect, select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.api import deps
from app.avisos.repositorio import AvisoRepository, PreferenciaRepository
from app.avisos.tabelas import AvisoTabela, PreferenciaAvisoTabela
from app.config import settings
from app.main import app
from app.mensageria.consumidor import ConsumidorWebhooks
from app.mensageria.produtor import ProdutorEventos
from app.persistence.repository import UsuarioRepository
from app.persistence.sessao import criar_engine, obter_sessao
from app.persistence.tabelas import UsuarioTabela
from app.persistence.tabelas_portfolio import ProjetoTabela, RiscoTabela, UsuarioProjetoTabela
from app.schemas.usuario import Perfil, UsuarioAutenticado
from app.webhooks.drive.recebimento import publicar_recebimento
from app.webhooks.modelos import Provedor, TipoEventoPortfolio
from app.webhooks.repositorio import FontePortfolioRepository, RecebimentoRepository
from app.webhooks.tabelas import (
    AuditoriaPortfolioTabela,
    FontePortfolioTabela,
    RecebimentoTabela,
    VersaoEntidadeTabela,
)
from app.webhooks.tratadores import montar_tratadores

pytestmark = pytest.mark.integracao

PORTA_GERENCIAMENTO = 15672
RISCO_TIPO = TipoEventoPortfolio.RISCO


@pytest.fixture
async def fabrica():
    engine = criar_engine()
    try:
        async with engine.connect() as conexao:
            tabelas = await conexao.run_sync(lambda s: inspect(s).get_table_names())
    except Exception:  # noqa: BLE001 — qualquer falha de conexão pula a suíte
        await engine.dispose()
        pytest.skip("PostgreSQL indisponível.")
    if "aviso" not in tabelas:
        await engine.dispose()
        pytest.skip("Tabela `aviso` ausente. Rode `alembic upgrade head`.")
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


@pytest.fixture
async def cenario(fabrica):
    """Projeto com um risco, quatro usuários e uma fonte do WH-02.

    A e B têm acesso ao projeto; C aderiu, mas não tem acesso; D tem
    acesso, mas com a preferência desligada.
    """
    sufixo = uuid.uuid4().hex[:8]
    projeto, outro = f"teste-{sufixo}", f"teste-{sufixo}-outro"
    risco = f"{projeto}-risco"
    usuarios = {nome: f"teste-{nome}-{sufixo}" for nome in "ABCD"}
    fonte = f"teste_{sufixo}"
    agora = datetime.now(UTC)
    async with fabrica() as sessao:
        for codigo in (projeto, outro):
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
        sessao.add(
            RiscoTabela(
                id=risco,
                projeto_codigo=projeto,
                descricao="risco sintético",
                probabilidade=3,
                impacto=4,
                status="monitorado",
                criado_em=agora,
                atualizado_em=agora,
            )
        )
        for nome, usuario_id in usuarios.items():
            await UsuarioRepository(sessao).garantir(
                usuario_id=usuario_id, nome=nome, perfil="membro_equipe"
            )
        await sessao.flush()
        for nome in "ABD":
            sessao.add(
                UsuarioProjetoTabela(
                    usuario_id=usuarios[nome],
                    projeto_codigo=projeto,
                    papel="membro",
                    criado_em=agora,
                )
            )
        preferencias = PreferenciaRepository(sessao)
        for nome, ativa, minimo in (
            ("A", True, 20),
            ("B", True, None),
            ("C", True, None),
            ("D", False, None),
        ):
            await preferencias.salvar(
                usuario_id=usuarios[nome],
                projeto_codigo=projeto,
                event_type=RISCO_TIPO,
                ativa=ativa,
                severidade_minima=minimo,
                agora=agora,
            )
        await FontePortfolioRepository(sessao).salvar(
            source_id=fonte,
            planilha_id="planilha",
            projetos={projeto},
            tipos={RISCO_TIPO},
            agora=agora,
        )
        await sessao.commit()
    dados = type("Cenario", (), {})()
    dados.projeto, dados.outro, dados.risco = projeto, outro, risco
    dados.usuarios, dados.fonte = usuarios, fonte
    yield dados
    async with fabrica() as sessao:
        ids = list(usuarios.values())
        await sessao.execute(delete(AvisoTabela).where(AvisoTabela.usuario_id.in_(ids)))
        await sessao.execute(
            delete(PreferenciaAvisoTabela).where(PreferenciaAvisoTabela.usuario_id.in_(ids))
        )
        for tabela in (AuditoriaPortfolioTabela, VersaoEntidadeTabela):
            await sessao.execute(delete(tabela).where(tabela.source_id == fonte))
        await sessao.execute(delete(RecebimentoTabela).where(RecebimentoTabela.fonte_id == fonte))
        await sessao.execute(
            delete(FontePortfolioTabela).where(FontePortfolioTabela.source_id == fonte)
        )
        await sessao.execute(
            delete(UsuarioProjetoTabela).where(UsuarioProjetoTabela.projeto_codigo == projeto)
        )
        await sessao.execute(delete(UsuarioTabela).where(UsuarioTabela.id.in_(ids)))
        await sessao.execute(delete(RiscoTabela).where(RiscoTabela.id == risco))
        await sessao.execute(
            delete(ProjetoTabela).where(ProjetoTabela.codigo.in_([projeto, outro]))
        )
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
async def enviar(fabrica, cenario, url_isolada):
    """Publica um evento de risco e espera o consumidor processá-lo."""
    produtor = ProdutorEventos(url_isolada, "prata.events", "prata.dead-letter")
    consumidor = ConsumidorWebhooks(
        url_isolada,
        exchange="prata.events",
        dead_letter_exchange="prata.dead-letter",
        fabrica=fabrica,
        tratadores=montar_tratadores(),
        max_retries=2,
        prefetch=5,
    )
    await consumidor.iniciar()

    async def publicar(versao, **dados):
        campos = {"status": "monitorado", "probabilidade": 3, "impacto": 4}
        campos.update(dados)
        evento = {
            "schema_version": 1,
            "event_id": str(uuid.uuid4()),
            "source_id": cenario.fonte,
            "event_type": RISCO_TIPO.value,
            "occurred_at": "2026-09-25T02:00:00Z",
            "projeto_codigo": cenario.projeto,
            "entity_id": cenario.risco,
            "version": versao,
            "data": campos,
        }
        async with fabrica() as sessao:
            recebimento, _ = await RecebimentoRepository(sessao).registrar(
                provedor=Provedor.APPS_SCRIPT,
                chave_externa=f"{cenario.fonte}:{evento['event_id']}",
                fonte_id=cenario.fonte,
                canal_id=None,
                evento={"provider": "apps_script", "event": evento},
                agora=datetime.now(UTC),
            )
            await sessao.commit()
        await publicar_recebimento(recebimento, fabrica=fabrica, produtor=produtor)
        for _ in range(50):
            async with fabrica() as sessao:
                registro = await sessao.get(RecebimentoTabela, recebimento.message_id)
                if registro.processado_em is not None:
                    break
            await asyncio.sleep(0.1)
        return evento, recebimento

    yield publicar
    await consumidor.encerrar()
    await produtor.encerrar()


async def avisados(fabrica, cenario, evento) -> list[str]:
    nomes = {usuario_id: nome for nome, usuario_id in cenario.usuarios.items()}
    async with fabrica() as sessao:
        linhas = await sessao.scalars(
            select(AvisoTabela).where(AvisoTabela.event_id == evento["event_id"])
        )
        return sorted(nomes[linha.usuario_id] for linha in linhas)


async def test_aviso_so_para_quem_aderiu_e_tem_acesso(enviar, fabrica, cenario):
    evento, _ = await enviar(2, probabilidade=5)  # 12 -> 20

    assert await avisados(fabrica, cenario, evento) == ["A", "B"]


async def test_reducao_de_risco_avisa_pelo_estado_anterior(enviar, fabrica, cenario):
    await enviar(2, probabilidade=5)  # 20
    evento, _ = await enviar(3, probabilidade=2)  # 8

    assert await avisados(fabrica, cenario, evento) == ["A", "B"]


async def test_abaixo_do_minimo_antes_e_depois_nao_avisa_quem_tem_minimo(enviar, fabrica, cenario):
    evento, _ = await enviar(2, probabilidade=3, impacto=3)  # 12 -> 9

    assert await avisados(fabrica, cenario, evento) == ["B"]


async def test_sem_diferenca_e_versao_antiga_nao_avisam(enviar, fabrica, cenario):
    await enviar(2, probabilidade=5)
    sem_diferenca, _ = await enviar(3, probabilidade=5)
    antiga, _ = await enviar(1, probabilidade=1)

    assert await avisados(fabrica, cenario, sem_diferenca) == []
    assert await avisados(fabrica, cenario, antiga) == []


async def test_reentrega_nao_duplica_aviso(enviar, fabrica, cenario, url_isolada):
    evento, recebimento = await enviar(2, probabilidade=5)
    produtor = ProdutorEventos(url_isolada, "prata.events", "prata.dead-letter")
    await publicar_recebimento(recebimento, fabrica=fabrica, produtor=produtor)
    await produtor.encerrar()
    await asyncio.sleep(1)

    assert await avisados(fabrica, cenario, evento) == ["A", "B"]


# --- Rotas ---------------------------------------------------------------------


@pytest.fixture
async def cliente(fabrica, monkeypatch):
    async def sessao_do_teste():
        async with fabrica() as sessao:
            yield sessao
            await sessao.commit()

    monkeypatch.setitem(app.dependency_overrides, obter_sessao, sessao_do_teste)
    transporte = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transporte, base_url="http://teste") as c:
        yield c


def como(monkeypatch, usuario_id, projetos):
    usuario = UsuarioAutenticado(
        id=usuario_id,
        nome="teste",
        email=None,
        perfil=Perfil.MEMBRO_EQUIPE,
        projetos=frozenset(projetos),
    )
    monkeypatch.setitem(app.dependency_overrides, deps.obter_usuario_atual, lambda: usuario)


async def criar_avisos(fabrica, cenario):
    """Dois avisos de A no projeto, um no outro projeto e um vencido."""
    agora = datetime.now(UTC)
    async with fabrica() as sessao:
        avisos = AvisoRepository(sessao)
        for indice, (projeto, quando) in enumerate(
            [
                (cenario.projeto, agora),
                (cenario.projeto, agora - timedelta(minutes=5)),
                (cenario.outro, agora),
                (cenario.projeto, agora - timedelta(days=31)),
            ]
        ):
            await avisos.criar(
                usuario_id=cenario.usuarios["A"],
                projeto_codigo=projeto,
                source_id=cenario.fonte,
                event_id=f"e{indice}",
                event_type=RISCO_TIPO,
                entity_id=cenario.risco,
                versao=indice + 1,
                diferencas={"status": {"de": "monitorado", "para": "mitigado"}},
                agora=quando,
            )
        await sessao.commit()


async def test_lista_so_avisos_visiveis_e_recentes(cliente, fabrica, cenario, monkeypatch):
    await criar_avisos(fabrica, cenario)
    como(monkeypatch, cenario.usuarios["A"], {cenario.projeto})

    lista = (await cliente.get("/avisos")).json()

    assert [aviso["versao"] for aviso in lista] == [1, 2]
    assert (await cliente.get("/avisos/contagem")).json() == {"nao_lidos": 2}


async def test_marcar_lido_reduz_a_contagem(cliente, fabrica, cenario, monkeypatch):
    await criar_avisos(fabrica, cenario)
    como(monkeypatch, cenario.usuarios["A"], {cenario.projeto})
    [primeiro, _] = (await cliente.get("/avisos")).json()

    assert (await cliente.post(f"/avisos/{primeiro['id']}/lido")).status_code == 204
    assert (await cliente.post(f"/avisos/{primeiro['id']}/lido")).status_code == 204
    assert (await cliente.get("/avisos/contagem")).json() == {"nao_lidos": 1}
    assert [a["versao"] for a in (await cliente.get("/avisos?nao_lidos=true")).json()] == [2]


async def test_aviso_de_outro_usuario_responde_404(cliente, fabrica, cenario, monkeypatch):
    await criar_avisos(fabrica, cenario)
    como(monkeypatch, cenario.usuarios["A"], {cenario.projeto})
    aviso_id = (await cliente.get("/avisos")).json()[0]["id"]
    como(monkeypatch, cenario.usuarios["B"], {cenario.projeto, cenario.outro})

    assert (await cliente.get(f"/avisos/{aviso_id}")).status_code == 404
    assert (await cliente.post(f"/avisos/{aviso_id}/lido")).status_code == 404
    assert (await cliente.get("/avisos")).json() == []


async def test_perder_o_acesso_oculta_os_avisos_antigos(cliente, fabrica, cenario, monkeypatch):
    await criar_avisos(fabrica, cenario)
    como(monkeypatch, cenario.usuarios["A"], {cenario.projeto})
    aviso_id = (await cliente.get("/avisos")).json()[0]["id"]
    como(monkeypatch, cenario.usuarios["A"], set())

    assert (await cliente.get("/avisos")).json() == []
    assert (await cliente.get("/avisos/contagem")).json() == {"nao_lidos": 0}
    assert (await cliente.get(f"/avisos/{aviso_id}")).status_code == 404


async def test_preferencias_respeitam_o_acesso_e_a_severidade(cliente, cenario, monkeypatch):
    como(monkeypatch, cenario.usuarios["A"], {cenario.projeto})
    base = f"/avisos/preferencias/{cenario.projeto}"

    salva = await cliente.put(
        f"{base}/risco.alterado", json={"ativa": True, "severidade_minima": 15}
    )
    fora = await cliente.put(
        f"/avisos/preferencias/{cenario.outro}/risco.alterado", json={"ativa": True}
    )
    marco = await cliente.put(
        f"{base}/marco.alterado", json={"ativa": True, "severidade_minima": 5}
    )

    assert (salva.status_code, salva.json()["severidade_minima"]) == (200, 15)
    assert fora.status_code == 403
    assert marco.status_code == 422
    listadas = (await cliente.get("/avisos/preferencias")).json()
    assert [(p["event_type"], p["ativa"]) for p in listadas] == [("risco.alterado", True)]


async def test_rotas_exigem_sessao(cliente):
    assert (await cliente.get("/avisos")).status_code == 401
    assert (await cliente.get("/avisos/preferencias")).status_code == 401
