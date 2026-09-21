"""Entrypoint do agendador de rotinas.

Processo separado da API, com o mesmo código. Duas razões (seção 8.4 de
docs/Arquitetura.md):

1. mantém a API sem estado, livre para reiniciar e escalar;
2. evita disparo duplicado — com o agendador embutido, duas réplicas da
   API produziriam dois relatórios para a diretoria no dia 5.

Este processo NÃO expõe HTTP. Ele importa o orquestrador em memória e o
aciona como qualquer outro canal; não chama a API por rede.

Execução local:
    python -m app.worker
"""

import asyncio
import logging
import signal
from collections.abc import Callable

from app.persistence import sessao
from app.rotinas.agendador import carregar_agenda, criar_agendador

logger = logging.getLogger(__name__)


def _registrar_sinais(evento_encerramento: asyncio.Event) -> Callable[[], None]:
    """Faz SIGINT/SIGTERM acordarem o ciclo assíncrono e devolve a limpeza.

    ``loop.add_signal_handler`` é o caminho usado no contêiner Linux. O
    fallback com ``signal.signal`` mantém a execução local no Windows, cujo
    loop não implementa a primeira API.
    """
    loop = asyncio.get_running_loop()
    registrados_no_loop: list[signal.Signals] = []
    anteriores: dict[signal.Signals, signal.Handlers] = {}

    def solicitar_encerramento(numero: int, _frame: object | None = None) -> None:
        logger.info("Sinal %s recebido; encerrando o worker", numero)
        loop.call_soon_threadsafe(evento_encerramento.set)

    for sinal in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sinal, solicitar_encerramento, sinal)
            registrados_no_loop.append(sinal)
        except NotImplementedError:
            anteriores[sinal] = signal.getsignal(sinal)
            signal.signal(sinal, solicitar_encerramento)

    def remover() -> None:
        for sinal in registrados_no_loop:
            loop.remove_signal_handler(sinal)
        for sinal, anterior in anteriores.items():
            signal.signal(sinal, anterior)

    return remover


async def principal(*, evento_encerramento: asyncio.Event | None = None) -> None:
    """Sobe o agendador e mantém o processo vivo.

    Passos previstos (onda 5):

    1. criar o engine do banco (persistence/sessao.py) — o jobstore do
       APScheduler usa o mesmo PostgreSQL;
    2. `rotinas.agendador.criar_agendador()` e `carregar_agenda()`, que
       reconcilia os jobs persistidos com a tabela de rotinas ativas;
    3. iniciar o scheduler e aguardar indefinidamente;
    4. no encerramento, parar o scheduler com `wait=True` para não
       interromper uma execução em curso no meio.
    """
    evento = evento_encerramento or asyncio.Event()
    remover_sinais = _registrar_sinais(evento) if evento_encerramento is None else lambda: None
    agendador = None

    sessao.iniciar()
    try:
        agendador = criar_agendador()
        # Pausado enquanto a tabela de rotinas é reconciliada com o jobstore:
        # nenhum job antigo pode disparar antes de seu estado atual ser lido.
        agendador.start(paused=True)
        await carregar_agenda()
        agendador.resume()
        logger.info("Worker de rotinas iniciado")

        await evento.wait()
    finally:
        remover_sinais()
        if agendador is not None and agendador.running:
            # Não interrompe uma rotina que já entrou no pipeline.
            agendador.shutdown(wait=True)
        await sessao.encerrar()
        logger.info("Worker de rotinas encerrado")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(principal())
