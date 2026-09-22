"""Porta do executor e os tipos da resposta.

Seção 3.1 de docs/plano-executor-proprio.md. Dois adaptadores:

- `copilot/client.py` — Copilot Studio via Direct Line, o caminho oficial;
- `rag/executor.py` — executor próprio, RAG sobre o corpus do Drive.

A escolha é de `settings.executor`, lida só em `api/deps.py`. O
orquestrador conhece esta porta e nenhum dos dois adaptadores: é o que
faz a troca ser uma linha no `.env`, e não um segundo caminho pelo
pipeline que pudesse contornar as guardas.

Diferença em relação ao desenho de 3.1: o identificador da sessão do
executor manteve o nome `conversa_externa_id`, que é o da coluna em
`Conversa`, em vez de virar `sessao_externa_id`. Renomear mudaria a
grafia em três camadas sem mudar o contrato.
"""

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class Fonte:
    """Uma referência verificável usada para compor a resposta."""

    documento: str  # nome do arquivo na pasta controlada
    link: str | None
    trecho: str  # o texto efetivamente entregue ao modelo
    score: float
    localizador: str  # seção, aba ou slide


@dataclass(frozen=True)
class TurnoContexto:
    """Um turno persistido, tratado como dado não confiável no prompt."""

    mensagem_usuario: str
    resposta_agente: str


@dataclass
class RespostaExecutor:
    """Resposta devolvida por qualquer executor."""

    texto: str
    # Sessão do lado do executor, para os próximos turnos (o
    # conversationId do Direct Line). `None` quando o executor não tem
    # sessão própria: o executor próprio guarda o estado no middleware (D6).
    conversa_externa_id: str | None = None
    # Vazio quando o executor não devolve citações — o Copilot, caixa-preta,
    # não devolve.
    fontes: tuple[Fonte, ...] = ()
    dados: dict | None = None  # anexos estruturados (cards, tabelas), se houver


@runtime_checkable
class Executor(Protocol):
    """Contrato dos executores.

    `runtime_checkable` pela mesma razão de `RepositorioVetorial`: o
    `isinstance` nos testes pega o método renomeado num adaptador antes
    que ele apareça na demonstração.
    """

    async def enviar(
        self,
        texto: str,
        intencao_id: str,
        exige_confirmacao: bool,
        conversa_externa_id: str | None = None,
        historico: tuple[TurnoContexto, ...] = (),
    ) -> RespostaExecutor:
        """Executa a mensagem já aprovada pelas guardas e devolve a resposta.

        `intencao_id` e `exige_confirmacao` são metadados, nunca texto
        concatenado à mensagem. Qualquer exceção é tratada pelo
        orquestrador como falha do executor. `historico` é opcional para
        manter compatibilidade com chamadores existentes.
        """
        ...
