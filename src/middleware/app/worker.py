"""Entrypoint do agendador de rotinas.

Processo separado da API, com o mesmo código. Duas razões (seção 8.4 de
documentos/Arquitetura.md):

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

logger = logging.getLogger(__name__)


async def principal() -> None:
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
    raise NotImplementedError("Worker a implementar na onda 5")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(principal())
