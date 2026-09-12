"""Divisão dos documentos em trechos que cabem no e5.

Cada trecho abre com uma linha de contexto — código, projeto, documento
e seção, aba ou slide — e segue com o corpo. A linha de contexto entra
no vetor de propósito: "Término: 30/06/2027" só é recuperável pela
pergunta "quando termina o Trecho Sul?" se o vetor souber de que projeto
e de que documento aquele prazo é.

O orçamento (`chunk_tokens`) é medido pelo mesmo tokenizador que vai
codificar (`embeddings.contar_tokens`), nunca por estimativa de
palavras: em tabela de cronograma, cheia de códigos e datas, a razão
entre tokens e caracteres é outra que em prosa. O teto duro de 512 do e5
é conferido no trecho montado — o que chega aqui acima dele é erro, e
não truncamento silencioso (risco da seção 8 do plano).

Regras de empacotamento:

- um trecho nunca atravessa grupo (seção, aba, slide) nem mistura
  permissões — é o que põe cada linha do consolidado do portfólio num
  trecho próprio, com o projeto e os perfis da própria linha;
- linha de tabela não é cortada. Só uma linha que sozinha estoura o
  orçamento é partida, entre células, repetindo a primeira célula (o
  identificador) em cada parte;
- a sobreposição (`chunk_overlap`) só vale para prosa: repetir uma linha
  de tabela no trecho seguinte duplicaria o registro.
"""

import re
from collections.abc import Callable, Iterable, Iterator, Sequence
from dataclasses import dataclass

from app.rag.embeddings import LIMITE_TOKENS, contar_tokens
from app.rag.ingestao.extracao import Unidade
from app.schemas.usuario import Perfil

Metadados = tuple[str | None, frozenset[Perfil]]

# Folga mínima entre o orçamento configurável e o teto do modelo. As
# contagens por pedaço incluem os tokens especiais de cada chamada e por
# isso SUPERestimam a soma; a folga cobre o prefixo `passage: `.
FOLGA_MINIMA = 16

_FIM_DE_FRASE = re.compile(r"(?<=[.!?;:])\s+")


class ErroChunking(ValueError):
    """Trecho montado acima do teto do encoder — erro de programação."""


@dataclass(frozen=True)
class TrechoPreparado:
    ordinal: int
    # Linha de contexto + corpo: exatamente o que vai ao encoder, menos o
    # prefixo `passage: `. É também o que o PostgreSQL guarda.
    texto: str
    tokens: int
    localizador: str
    projeto: str | None
    perfis: frozenset[Perfil]


@dataclass(frozen=True)
class _Pedaco:
    texto: str
    tokens: int
    prosa: bool


def dividir(
    unidades: Sequence[Unidade],
    *,
    cabecalho: str,
    metadados: Callable[[Unidade], Metadados],
    limite: int,
    sobreposicao: int,
) -> list[TrechoPreparado]:
    """Empacota as unidades em trechos de até `limite` tokens."""
    if limite > LIMITE_TOKENS - FOLGA_MINIMA:
        raise ValueError(
            f"chunk_tokens={limite} não deixa folga para o teto de {LIMITE_TOKENS} tokens do e5"
        )

    montados: list[tuple[str, str, Metadados]] = []
    for grupo, meta, bloco in _agrupar(unidades, metadados):
        topo = f"{cabecalho}\n{grupo}" if grupo else cabecalho
        orcamento = limite - _tokens(topo)
        if orcamento <= 0:
            raise ErroChunking(f"a linha de contexto sozinha estoura o orçamento: {topo[:80]!r}")

        atual: list[_Pedaco] = []
        soma = 0
        for pedaco in (p for unidade in bloco for p in _caber(unidade, orcamento)):
            if atual and soma + pedaco.tokens > orcamento:
                montados.append((_juntar(topo, atual), grupo, meta))
                atual = _sobra(atual, sobreposicao)
                soma = sum(p.tokens for p in atual)
                if soma + pedaco.tokens > orcamento:
                    atual, soma = [], 0
            atual.append(pedaco)
            soma += pedaco.tokens
        if atual:
            montados.append((_juntar(topo, atual), grupo, meta))

    trechos = []
    for ordinal, (texto, grupo, (projeto, perfis)) in enumerate(montados, start=1):
        tokens = contar_tokens(texto)
        if tokens > LIMITE_TOKENS:
            raise ErroChunking(
                f"trecho {ordinal} com {tokens} tokens, acima do teto de {LIMITE_TOKENS}"
            )
        trechos.append(TrechoPreparado(ordinal, texto, tokens, grupo, projeto, perfis))
    return trechos


def _tokens(texto: str) -> int:
    return contar_tokens(texto, prefixo="")


def _agrupar(
    unidades: Iterable[Unidade], metadados: Callable[[Unidade], Metadados]
) -> Iterator[tuple[str, Metadados, list[Unidade]]]:
    """Blocos de unidades consecutivas com o mesmo grupo e a mesma permissão."""
    chave: tuple[str, Metadados] | None = None
    bloco: list[Unidade] = []
    for unidade in unidades:
        desta = (unidade.grupo, metadados(unidade))
        if bloco and desta != chave:
            yield chave[0], chave[1], bloco  # type: ignore[index]
            bloco = []
        chave = desta
        bloco.append(unidade)
    if bloco:
        yield chave[0], chave[1], bloco  # type: ignore[index]


def _caber(unidade: Unidade, orcamento: int) -> list[_Pedaco]:
    """A unidade inteira, ou partida em pedaços que caibam no orçamento."""
    tokens = _tokens(unidade.texto)
    if tokens <= orcamento:
        return [_Pedaco(unidade.texto, tokens, prosa=not unidade.indivisivel)]
    if unidade.indivisivel:
        celulas = unidade.texto.split(" | ")
        return _empacotar(
            celulas, orcamento, separador=" | ", prefixo=f"{celulas[0]} (cont.) | ", prosa=False
        )
    return _empacotar(
        _FIM_DE_FRASE.split(unidade.texto), orcamento, separador=" ", prefixo="", prosa=True
    )


def _empacotar(
    partes: Sequence[str], orcamento: int, *, separador: str, prefixo: str, prosa: bool
) -> list[_Pedaco]:
    pedacos: list[str] = []
    atual = ""
    for parte in _quebrar_longas(partes, orcamento):
        candidato = f"{atual}{separador}{parte}" if atual else parte
        if atual and _tokens(candidato) > orcamento:
            pedacos.append(atual)
            atual = f"{prefixo}{parte}"
        else:
            atual = candidato
    if atual:
        pedacos.append(atual)
    return [_Pedaco(pedaco, _tokens(pedaco), prosa) for pedaco in pedacos]


def _quebrar_longas(partes: Iterable[str], orcamento: int) -> Iterator[str]:
    """Parte por palavras o que nem sozinho cabe em metade do orçamento.

    Metade, e não o orçamento inteiro, para sobrar espaço ao prefixo que
    repete o identificador da linha nas partes seguintes.
    """
    teto = max(orcamento // 2, 8)
    for parte in partes:
        if _tokens(parte) <= teto:
            yield parte
            continue
        atual: list[str] = []
        for palavra in parte.split():
            if atual and _tokens(" ".join([*atual, palavra])) > teto:
                yield " ".join(atual)
                atual = []
            atual.append(palavra)
        if atual:
            yield " ".join(atual)


def _sobra(pedacos: list[_Pedaco], sobreposicao: int) -> list[_Pedaco]:
    """O fim do trecho anterior que abre o seguinte — só prosa."""
    if sobreposicao <= 0:
        return []
    mantidos: list[_Pedaco] = []
    soma = 0
    for pedaco in reversed(pedacos):
        if not pedaco.prosa or soma + pedaco.tokens > sobreposicao:
            break
        mantidos.insert(0, pedaco)
        soma += pedaco.tokens
    # Repetir o trecho anterior inteiro não é sobreposição, é duplicata.
    return mantidos if len(mantidos) < len(pedacos) else []


def _juntar(topo: str, pedacos: list[_Pedaco]) -> str:
    return topo + "\n" + "\n".join(pedaco.texto for pedaco in pedacos)
