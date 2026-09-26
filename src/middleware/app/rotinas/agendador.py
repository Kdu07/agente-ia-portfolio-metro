"""Agenda dos prompts pré-programados.

APScheduler com jobstore SQLAlchemy sobre o PostgreSQL que já existe: a
agenda fica persistida no mesmo banco das interações, sem Redis, sem
broker e sem um quinto serviço no compose.

Roda no contêiner `worker`, separado da API. Duas razões: mantém a API
sem estado e evita disparo duplicado quando ela reinicia ou escala — com
o agendador embutido, duas réplicas da API produziriam dois relatórios.

Dois detalhes operacionais que este módulo precisa tratar explicitamente,
sob pena de a rotina disparar na hora errada ou várias vezes:

**Fuso.** "Todo dia 5 às 8h" significa 8h no fuso de quem cadastrou. O
`CronTrigger` recebe `timezone=rotina.timezone` — um cron interpretado em
UTC erra a hora durante boa parte do ano.

**Disparo perdido.** Se o worker estiver fora do ar no horário, o padrão
do APScheduler é descartar o disparo ou reexecutar em rajada ao voltar.
`coalesce=True` colapsa disparos acumulados num só e
`misfire_grace_time` define até quando um disparo atrasado ainda vale.
Sem os dois, o relatório do dia 5 sai três vezes às 14h.
"""

from __future__ import annotations

from datetime import UTC
from zoneinfo import ZoneInfo

from apscheduler.job import Job
from apscheduler.jobstores.base import JobLookupError
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.engine import make_url

from app.config import settings
from app.persistence.models import Rotina
from app.persistence.repository import RotinaRepository
from app.persistence.sessao import fabrica_de_sessoes

# Colapsa disparos acumulados durante uma indisponibilidade num único.
COALESCE = True

# Janela em que um disparo atrasado ainda é considerado válido. Uma hora:
# além disso, o relatório perdeu utilidade e é melhor pular do que enviar
# fora de contexto.
MISFIRE_GRACE_TIME_SEGUNDOS = 3600

# Uma execução por rotina por vez. Se a anterior ainda roda, a nova é
# descartada em vez de concorrer com ela.
MAX_INSTANCES = 1

PREFIXO_JOB_ROTINA = "rotina:"
JOB_RECONCILIACAO_ID = "sistema:reconciliar-rotinas"

_agendador: AsyncIOScheduler | None = None


def _url_sincrona_jobstore(database_url: str) -> str:
    """Troca o driver assíncrono pelo driver síncrono do jobstore.

    O resto da URL passa intacto, com uma exceção: o TLS. O asyncpg o lê
    em `ssl=require`, e o psycopg só entende `sslmode=require` — e recusa
    a conexão ao ver o parâmetro que não conhece. Sem a tradução, a mesma
    `DATABASE_URL` que funciona na API derrubaria o worker no banco
    gerenciado, que exige TLS.
    """
    url = make_url(database_url)
    drivers = {
        "postgresql+asyncpg": "postgresql+psycopg",
        "sqlite+aiosqlite": "sqlite+pysqlite",
    }
    driver = drivers.get(url.drivername, url.drivername)
    if driver.endswith(("+asyncpg", "+aiosqlite")):
        raise ValueError(f"Driver assíncrono sem equivalente para o jobstore: {url.drivername}")
    consulta = dict(url.query)
    if driver == "postgresql+psycopg" and "ssl" in consulta:
        consulta["sslmode"] = consulta.pop("ssl")
    return url.set(drivername=driver, query=consulta).render_as_string(hide_password=False)


def _obter_agendador() -> AsyncIOScheduler:
    if _agendador is None:
        raise RuntimeError("O agendador ainda não foi criado")
    return _agendador


def _id_job(rotina_id: str) -> str:
    return f"{PREFIXO_JOB_ROTINA}{rotina_id}"


def criar_agendador() -> AsyncIOScheduler:
    """Cria uma única instância com jobstore persistente no PostgreSQL.

    O worker deve iniciá-la em modo pausado, executar ``carregar_agenda``
    e somente então liberar os disparos.
    """
    global _agendador
    if _agendador is not None:
        return _agendador

    _agendador = AsyncIOScheduler(
        jobstores={
            "default": SQLAlchemyJobStore(
                url=_url_sincrona_jobstore(settings.database_url),
                tablename="apscheduler_jobs",
                engine_options={"pool_pre_ping": True},
            )
        },
        job_defaults={
            "coalesce": COALESCE,
            "misfire_grace_time": MISFIRE_GRACE_TIME_SEGUNDOS,
            "max_instances": MAX_INSTANCES,
        },
        timezone=UTC,
    )
    _agendador.add_job(
        carregar_agenda,
        trigger=IntervalTrigger(
            seconds=settings.rotinas_reconciliacao_segundos,
            timezone=UTC,
        ),
        id=JOB_RECONCILIACAO_ID,
        name="Reconciliar rotinas ativas",
        replace_existing=True,
    )
    return _agendador


async def carregar_agenda() -> None:
    """Reconstrói a agenda a partir das rotinas ativas.

    Chamado na subida do worker. O jobstore persiste os jobs, mas a
    reconciliação com a tabela de rotinas é o que garante que uma rotina
    editada ou desativada enquanto o worker estava fora entre em vigor.
    """
    agendador = _obter_agendador()
    if not agendador.running:
        raise RuntimeError("Inicie o agendador pausado antes de reconciliar a agenda")

    async with fabrica_de_sessoes()() as sessao:
        rotinas = await RotinaRepository(sessao).listar_ativas()

    ids_ativos = {rotina.id for rotina in rotinas}
    for rotina in rotinas:
        agendar(rotina)

    for job in listar_agendadas():
        rotina_id = job.id.removeprefix(PREFIXO_JOB_ROTINA)
        if rotina_id not in ids_ativos:
            desagendar(rotina_id)


def agendar(rotina: Rotina) -> None:
    """Registra ou atualiza o job de uma rotina."""
    if not rotina.ativa:
        desagendar(rotina.id)
        return

    trigger = CronTrigger.from_crontab(
        rotina.agenda_cron,
        timezone=ZoneInfo(rotina.timezone),
    )
    _obter_agendador().add_job(
        executar_rotina_agendada,
        trigger=trigger,
        args=[rotina.id],
        id=_id_job(rotina.id),
        name=rotina.nome,
        replace_existing=True,
        coalesce=COALESCE,
        misfire_grace_time=MISFIRE_GRACE_TIME_SEGUNDOS,
        max_instances=MAX_INSTANCES,
    )


def desagendar(rotina_id: str) -> None:
    """Remove o job de uma rotina desativada ou excluída."""
    try:
        _obter_agendador().remove_job(_id_job(rotina_id))
    except JobLookupError:
        pass


def listar_agendadas() -> list[Job]:
    """Lista somente os jobs de rotinas, sem expor jobs internos."""
    return [
        job
        for job in _obter_agendador().get_jobs()
        if job.id.startswith(PREFIXO_JOB_ROTINA)
    ]


async def executar_rotina_agendada(rotina_id: str) -> None:
    """Busca o estado atual da rotina e o entrega ao executor da task #406."""
    async with fabrica_de_sessoes()() as sessao:
        rotina = await RotinaRepository(sessao).obter(rotina_id)

    if rotina is None or not rotina.ativa:
        desagendar(rotina_id)
        return

    # Import tardio evita acoplar a inicialização do scheduler ao grafo do
    # pipeline. A implementação do executor pertence à task #406.
    from app.rotinas.execucao import executar

    await executar(rotina)
