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

from app.persistence.models import Rotina

# Colapsa disparos acumulados durante uma indisponibilidade num único.
COALESCE = True

# Janela em que um disparo atrasado ainda é considerado válido. Uma hora:
# além disso, o relatório perdeu utilidade e é melhor pular do que enviar
# fora de contexto.
MISFIRE_GRACE_TIME_SEGUNDOS = 3600

# Uma execução por rotina por vez. Se a anterior ainda roda, a nova é
# descartada em vez de concorrer com ela.
MAX_INSTANCES = 1


def criar_agendador():
    """Instancia o AsyncIOScheduler com jobstore no PostgreSQL.

    TODO (onda 5): configurar SQLAlchemyJobStore sobre settings.database_url
    com os parâmetros acima como defaults do job.
    """
    raise NotImplementedError("Agendador a implementar na onda 5")


async def carregar_agenda() -> None:
    """Reconstrói a agenda a partir das rotinas ativas.

    Chamado na subida do worker. O jobstore persiste os jobs, mas a
    reconciliação com a tabela de rotinas é o que garante que uma rotina
    editada ou desativada enquanto o worker estava fora entre em vigor.
    """
    raise NotImplementedError("Agendador a implementar na onda 5")


def agendar(rotina: Rotina) -> None:
    """Registra ou atualiza o job de uma rotina."""
    raise NotImplementedError("Agendador a implementar na onda 5")


def desagendar(rotina_id: str) -> None:
    """Remove o job de uma rotina desativada ou excluída."""
    raise NotImplementedError("Agendador a implementar na onda 5")
