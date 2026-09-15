"""Executor próprio — adaptador da porta `Executor` sobre o RAG.

Seção 3.1 do plano: o que o orquestrador aciona no passo 4 quando
`settings.executor` é `proprio`. Não acrescenta lógica ao RAG: traduz a
porta para `FluxoRag.responder` e a `RespostaRag` de volta para
`RespostaExecutor`.

**Roteamento da V1.** A tabela da seção 3.5 manda os registros para a
base estruturada e só a prosa para o RAG. A base (`app/portfolio/`)
ainda não existe, então toda intenção que passa pelas guardas vem para
cá — transações inclusive, que tendem a terminar em abstenção.
`intencao_id` e `exige_confirmacao` entram pela porta e passam a decidir
o caminho quando a base existir.

**Escopo fixo por instância.** A porta não recebe o usuário, e o escopo
da recuperação é o dele. Por isso o executor é montado por requisição
(`montar_executor`, chamado em `api/deps.py`), com o escopo já
resolvido. `projetos` vai vazio enquanto `UsuarioAutenticado` não
carregar a alocação: líder e membro de equipe alcançam só documentos
transversais, que é o resultado conservador (ver `Escopo`).

**Sem sessão externa.** O estado da conversa é do middleware (D6), e
`conversa_externa_id` volta `None`. Os turnos anteriores ainda não
entram no contexto: cada pergunta é respondida sozinha.

**Fontes no texto.** A resposta leva ao fim um bloco com o arquivo e o
local de cada citação, na ordem dos números entre colchetes. É o que a
interface mostra hoje, e é o que fica gravado no registro da interação.
As fontes estruturadas seguem em `RespostaExecutor.fontes`. A abstenção
não tem bloco, porque não cita nada.

`ErroGeracao` propaga: indisponibilidade do modelo não é abstenção, e o
orquestrador a registra como falha do executor.
"""

from collections.abc import Sequence
from typing import Any

from app.executor.base import Fonte, RespostaExecutor
from app.rag.fluxo import FluxoRag, montar_fluxo
from app.rag.vetorial.base import Escopo
from app.schemas.usuario import UsuarioAutenticado


class ExecutorRag:
    """Implementa `Executor` respondendo pelo fluxo de RAG."""

    def __init__(self, fluxo: FluxoRag, escopo: Escopo) -> None:
        self._fluxo = fluxo
        self._escopo = escopo

    async def enviar(
        self,
        texto: str,
        intencao_id: str,
        exige_confirmacao: bool,
        conversa_externa_id: str | None = None,
    ) -> RespostaExecutor:
        """Responde pelo RAG, no escopo de quem pergunta."""
        resultado = await self._fluxo.responder(texto, self._escopo)
        fontes = tuple(
            Fonte(
                documento=fonte.documento,
                link=fonte.link,
                trecho=fonte.trecho,
                score=fonte.score,
                localizador=fonte.localizador,
            )
            for fonte in resultado.resposta.fontes
        )
        return RespostaExecutor(texto=com_fontes(resultado.resposta.texto, fontes), fontes=fontes)


def com_fontes(texto: str, fontes: Sequence[Fonte]) -> str:
    """Acrescenta ao texto a lista de fontes, numerada como as citações."""
    if not fontes:
        return texto
    linhas = [
        f"[{numero}] {fonte.documento}" + (f" — {fonte.localizador}" if fonte.localizador else "")
        for numero, fonte in enumerate(fontes, start=1)
    ]
    return f"{texto}\n\nFontes:\n" + "\n".join(linhas)


def montar_executor(sessao: Any, usuario: UsuarioAutenticado) -> ExecutorRag:
    """Executor com os adaptadores do `.env` e o escopo do usuário."""
    return ExecutorRag(montar_fluxo(sessao), Escopo(perfil=usuario.perfil))
