"""Fluxo de RAG ponta a ponta: pergunta e escopo entram, resposta com fontes sai.

    consulta → preparação → embedding → busca no índice com filtro de
    permissão → texto no PostgreSQL → montagem do contexto → modelo de
    linguagem → resposta com fontes (ou abstenção)

Compõe `recuperacao.py` e `geracao.py` sem acrescentar lógica a nenhum
dos dois. É o que `rag/executor.py` chamará quando o executor próprio
for ligado ao orquestrador (seção 3.1 do plano); até lá, é o que servem
o comando `scripts.perguntar_rag` e a bancada.

O `Escopo` vem de quem chama, e não é deduzido aqui: perfil e projetos
são resolvidos na autenticação, e um fluxo que os adivinhasse seria um
segundo lugar decidindo quem pode ler o quê.

**Rastreabilidade.** Cada consulta deixa uma linha de log com a
situação, o modelo, o perfil, os trechos recuperados com seus scores e
os que a resposta citou — identificadores, nunca texto. É o que permite
reconstruir de onde veio uma resposta sem copiar o corpus para o log.
"""

import logging
import time
from dataclasses import dataclass
from typing import Any

from app.rag.geracao import Gerador, RespostaRag
from app.rag.recuperacao import Recuperacao, Recuperador
from app.rag.vetorial.base import Escopo

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ResultadoRag:
    """A resposta e a recuperação que a sustentou.

    A recuperação acompanha a resposta porque é o que a bancada mede
    (recall@k) e o que um diagnóstico precisa ver: resposta errada com
    trecho certo recuperado é defeito de geração; sem o trecho, de
    recuperação (seção 5.1 do plano).
    """

    resposta: RespostaRag
    recuperacao: Recuperacao
    latencia_ms: int


class FluxoRag:
    """Encadeia recuperação e geração para uma pergunta."""

    def __init__(self, recuperador: Recuperador, gerador: Gerador) -> None:
        self._recuperador = recuperador
        self._gerador = gerador

    async def responder(self, pergunta: str, escopo: Escopo) -> ResultadoRag:
        inicio = time.perf_counter()
        recuperacao = await self._recuperador.recuperar(pergunta, escopo)
        resposta = await self._gerador.responder(recuperacao)
        latencia_ms = int((time.perf_counter() - inicio) * 1000)

        logger.info(
            "RAG situacao=%s modelo=%s perfil=%s recuperados=%s citados=%s latencia_ms=%d",
            resposta.situacao.value,
            resposta.modelo,
            escopo.perfil.value,
            [f"{t.trecho_id}:{t.score:.3f}" for t in recuperacao.trechos],
            [fonte.trecho_id for fonte in resposta.fontes],
            latencia_ms,
        )
        return ResultadoRag(resposta=resposta, recuperacao=recuperacao, latencia_ms=latencia_ms)


def montar_fluxo(sessao: Any) -> FluxoRag:
    """Fluxo com os adaptadores e parâmetros do `.env`.

    O modelo de linguagem é montado antes de qualquer consulta: chave
    ausente falha aqui, nomeada, e não depois de pagar o embedding e a
    busca.
    """
    from app.rag.linguagem.fabrica import obter_modelo_linguagem
    from app.rag.recuperacao import montar_recuperador

    modelo = obter_modelo_linguagem()
    return FluxoRag(montar_recuperador(sessao), Gerador(modelo))
