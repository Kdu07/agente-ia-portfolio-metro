"""Recuperação: da pergunta aos trechos que podem sustentar a resposta.

Trajeto da seção 3.3 do plano do executor próprio, na parte que vem
antes do modelo de geração:

    pergunta → preparação → embedding (e5, local) → busca com filtro de
    permissão (índice) → texto dos trechos (PostgreSQL) → conferência

Este módulo não conhece o modelo de linguagem, e `geracao.py` não
conhece o índice. É o corte que permite trocar um sem tocar o outro.

**A permissão é aplicada duas vezes, e as duas não são redundantes.** A
primeira é o filtro na consulta ao índice (invariante 2 de
`vetorial/base.py`), que é a que protege: sem ela os `k` trechos já
conteriam o que o usuário não pode ver. A segunda é a conferência do
texto lido do PostgreSQL contra a permissão gravada junto dele
(`Escopo.alcanca`). Ela só age quando os dois lados divergem — a
ingestão caiu entre o `upsert` e o commit, ou uma classificação revista
chegou a um e não ao outro —, e nesse caso descartar e registrar é o
comportamento correto: na dúvida, menos gente lê.

**O que se registra no log são identificadores, nunca texto.** Rastrear
quais trechos sustentaram uma resposta é exigência de rastreabilidade;
copiar o conteúdo deles para o log multiplicaria os lugares onde o
corpus vive.
"""

import asyncio
import logging
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Protocol

from app.config import settings
from app.rag.embeddings import codificar_consulta
from app.rag.ingestao.registro import TrechoLido
from app.rag.vetorial.base import Escopo, RepositorioVetorial

logger = logging.getLogger(__name__)


class LeitorTrechos(Protocol):
    """Quem devolve o texto dos trechos pelo identificador.

    `RegistroIngestao` implementa; os testes dublam. O protocolo existe
    para que a recuperação dependa do que usa — ler texto por id —, e não
    da classe inteira de registro da ingestão.
    """

    async def textos(self, trecho_ids: Sequence[str]) -> Mapping[str, TrechoLido]: ...


@dataclass(frozen=True)
class TrechoRecuperado:
    """Um trecho visível ao escopo, com o texto e a similaridade."""

    trecho_id: str
    documento_id: str
    texto: str
    localizador: str
    nome_arquivo: str
    link: str | None
    projeto: str | None
    score: float


@dataclass(frozen=True)
class Recuperacao:
    """O que a busca produziu para uma pergunta, na ordem de similaridade.

    Os dois contadores não são diagnóstico ornamental: um vetor sem
    texto ou fora do escopo no banco é sinal de índice e PostgreSQL
    dessincronizados, e sem contagem essa condição só apareceria como
    "o RAG respondeu pior hoje".
    """

    consulta: str
    trechos: tuple[TrechoRecuperado, ...]
    sem_texto: int = 0
    fora_do_escopo: int = 0

    @property
    def vazia(self) -> bool:
        return not self.trechos


def preparar_consulta(texto: str) -> str:
    """Normaliza a pergunta antes de vetorizá-la.

    Só espaços: quebras de linha e tabulações vindas do ditado ou de um
    colar não mudam o sentido e mudam o vetor. Nada de minúsculas nem de
    remoção de acentos — o e5 foi treinado sobre texto natural, e o
    código de projeto em maiúsculas é justamente o que ancora a busca.
    """
    preparado = " ".join(texto.split())
    if not preparado:
        raise ValueError("consulta vazia")
    return preparado


class Recuperador:
    """Busca os trechos que um escopo pode ver e que respondem à pergunta."""

    def __init__(
        self,
        repositorio: RepositorioVetorial,
        leitor: LeitorTrechos,
        *,
        k: int,
        score_minimo: float,
        codificar: Callable[[str], Sequence[float]] = codificar_consulta,
    ) -> None:
        """Recebe os colaboradores prontos — os testes dublam os três."""
        if k < 1:
            raise ValueError(f"k deve ser ao menos 1; recebido {k}")
        self._repositorio = repositorio
        self._leitor = leitor
        self._k = k
        self._score_minimo = score_minimo
        self._codificar = codificar

    async def recuperar(self, consulta: str, escopo: Escopo) -> Recuperacao:
        """Devolve os trechos visíveis ao escopo, do mais similar ao menos."""
        texto = preparar_consulta(consulta)

        # O encoder roda na CPU por centenas de milissegundos. Fora de uma
        # thread, congelaria o laço de eventos e todas as outras
        # requisições do processo — mesma razão do `to_thread` do Pinecone.
        vetor = await asyncio.to_thread(self._codificar, texto)
        acertos = await self._repositorio.buscar(
            vetor, escopo=escopo, k=self._k, score_minimo=self._score_minimo
        )
        lidos = await self._leitor.textos([acerto.trecho_id for acerto in acertos])

        trechos: list[TrechoRecuperado] = []
        sem_texto: list[str] = []
        fora_do_escopo: list[str] = []
        for acerto in acertos:
            lido = lidos.get(acerto.trecho_id)
            if lido is None:
                sem_texto.append(acerto.trecho_id)
                continue
            if not escopo.alcanca(lido.projeto, lido.perfis):
                fora_do_escopo.append(acerto.trecho_id)
                continue
            trechos.append(
                TrechoRecuperado(
                    trecho_id=lido.trecho_id,
                    documento_id=lido.documento_id,
                    texto=lido.texto,
                    localizador=lido.localizador,
                    nome_arquivo=lido.nome_arquivo,
                    link=lido.link,
                    projeto=lido.projeto,
                    score=acerto.score,
                )
            )

        if sem_texto:
            logger.warning(
                "Vetores sem texto no PostgreSQL — índice e banco dessincronizados: %s",
                sem_texto,
            )
        if fora_do_escopo:
            logger.warning(
                "Trechos devolvidos pelo índice fora do escopo no PostgreSQL (perfil=%s): %s",
                escopo.perfil.value,
                fora_do_escopo,
            )

        return Recuperacao(
            consulta=texto,
            trechos=tuple(trechos),
            sem_texto=len(sem_texto),
            fora_do_escopo=len(fora_do_escopo),
        )


def montar_recuperador(sessao: Any) -> Recuperador:
    """Recuperador com os colaboradores e os parâmetros do `.env`.

    Recebe a `AsyncSession` porque o texto dos trechos vive no
    PostgreSQL — e o adaptador pgvector, se acionado, também a usa.
    """
    from app.rag.ingestao.registro import RegistroIngestao
    from app.rag.vetorial.fabrica import obter_repositorio_vetorial

    return Recuperador(
        obter_repositorio_vetorial(sessao),
        RegistroIngestao(sessao),
        k=settings.rag_top_k,
        score_minimo=settings.rag_score_minimo,
    )
