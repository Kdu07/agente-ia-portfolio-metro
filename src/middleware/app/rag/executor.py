"""Executor próprio — adaptador da porta `Executor` sobre o RAG.

Seção 3.1 do plano: o que o orquestrador aciona no passo 4 quando
`settings.executor` é `proprio`. Não acrescenta lógica ao RAG: traduz a
porta para `FluxoRag.responder` e a `RespostaRag` de volta para
`RespostaExecutor`.

**Roteamento da V1.** A tabela da seção 3.5 manda os registros para a
base estruturada e só a prosa para o RAG. O schema `portfolio` já existe
(`persistence/tabelas_portfolio.py`, com rotas só de leitura em
`api/routes/portfolio.py`), mas este executor ainda não o consulta: toda
intenção que passa pelas guardas vem para cá, transações inclusive.
`intencao_id` e `exige_confirmacao` entram pela porta e passam a decidir
o caminho quando o executor ler a base; hoje `exige_confirmacao` só muda
o texto da abstenção (ver abaixo).

**Escopo fixo por instância.** A porta não recebe o usuário, e o escopo
da recuperação é o dele. Por isso o executor é montado por requisição
(`montar_executor`, chamado em `api/deps.py`), com o escopo já
resolvido. `projetos` vai vazio enquanto `UsuarioAutenticado` não
carregar a alocação: líder e membro de equipe alcançam só documentos
transversais, que é o resultado conservador (ver `Escopo`).

**Sem sessão externa.** O estado da conversa é do middleware (D6), e
`conversa_externa_id` volta `None`. Os turnos anteriores enriquecem a
geração, mas não a consulta vetorial: a busca usa somente a mensagem
atual para não diluir sua semântica com assuntos passados.

**Fontes no texto.** A resposta leva ao fim um bloco com o arquivo e o
local de cada citação, na ordem dos números entre colchetes. É o que a
interface mostra hoje, e é o que fica gravado no registro da interação.
As fontes estruturadas seguem em `RespostaExecutor.fontes`. A abstenção
não tem bloco, porque não cita nada.

**Transação sem resposta não vira "não encontrei".** Pedido que altera
dado — "muda a data de conclusão do Monotrilho Ouro" — chega com
`exige_confirmacao`. O executor próprio só lê documentos: sem a base
estruturada, não há onde gravar a alteração nem o que confirmar. O
pedido ainda assim passa pelo RAG, porque o classificador às vezes toma
por transação uma pergunta — "qual é o custo total no termo de
abertura?" sai como `atualizar_termo_abertura` —, e a resposta que o RAG
der vale mais que a recusa. Só quando o RAG se abstém a abstenção dá
lugar à explicação de que alterações não são feitas por este canal: a
quem pediu uma mudança, "não encontrei informação suficiente" diria que
faltou dado.

`ErroGeracao` propaga: indisponibilidade do modelo não é abstenção, e o
orquestrador a registra como falha do executor.
"""

from collections.abc import Sequence
from typing import Any

from app.executor.base import Fonte, RespostaExecutor, TurnoContexto
from app.rag.fluxo import FluxoRag, montar_fluxo
from app.rag.vetorial.base import Escopo
from app.schemas.usuario import UsuarioAutenticado

TEXTO_TRANSACAO = (
    "Alterações no portfólio, como mudar datas, registrar riscos ou encerrar projetos, "
    "ainda não são feitas por este canal. Aqui eu consulto o que os documentos dos "
    "projetos registram: se quiser, pergunte, por exemplo, qual é a data de conclusão "
    "prevista hoje."
)


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
        historico: tuple[TurnoContexto, ...] = (),
    ) -> RespostaExecutor:
        """Responde pelo RAG, no escopo de quem pergunta."""
        if historico:
            resultado = await self._fluxo.responder(
                texto,
                self._escopo,
                pergunta_para_geracao=compor_prompt(texto, historico),
            )
        else:
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
        if exige_confirmacao and not resultado.resposta.respondida:
            return RespostaExecutor(texto=TEXTO_TRANSACAO)
        return RespostaExecutor(texto=com_fontes(resultado.resposta.texto, fontes), fontes=fontes)


def compor_prompt(texto: str, historico: tuple[TurnoContexto, ...]) -> str:
    """Delimita o historico como dado antes da mensagem atual.

    As respostas anteriores entram sem o bloco de fontes que `com_fontes`
    acrescentou: os números delas se referem a documentos de outra
    consulta, e o modelo tende a imitar a forma do que lê no histórico —
    passaria a escrever a própria lista de fontes.
    """
    if not historico:
        return texto
    turnos = "\n".join(
        f"<turno>\n<mensagem_usuario>{turno.mensagem_usuario}</mensagem_usuario>\n"
        f"<resposta_agente>{sem_fontes(turno.resposta_agente)}</resposta_agente>\n</turno>"
        for turno in historico
    )
    return f"<historico_nao_confiavel>\n{turnos}\n</historico_nao_confiavel>\n<mensagem_atual>{texto}</mensagem_atual>"


_SEPARADOR_FONTES = "\n\nFontes:\n"


def sem_fontes(texto: str) -> str:
    """O texto de uma resposta sem o bloco de fontes de `com_fontes`."""
    return texto.split(_SEPARADOR_FONTES, 1)[0]


def com_fontes(texto: str, fontes: Sequence[Fonte]) -> str:
    """Acrescenta ao texto a lista de fontes, numerada como as citações."""
    if not fontes:
        return texto
    linhas = [
        f"[{numero}] {fonte.documento}" + (f" — {fonte.localizador}" if fonte.localizador else "")
        for numero, fonte in enumerate(fontes, start=1)
    ]
    return texto + _SEPARADOR_FONTES + "\n".join(linhas)


def montar_executor(sessao: Any, usuario: UsuarioAutenticado) -> ExecutorRag:
    """Executor com os adaptadores do `.env` e o escopo do usuário."""
    return ExecutorRag(
        montar_fluxo(sessao),
        Escopo(perfil=usuario.perfil, projetos=usuario.projetos),
    )
