"""Bancada de avaliação do RAG — seção 5 do plano do executor próprio.

Roda o conjunto de referência (`dados/bancada-rag.csv`) pelo fluxo real
— índice, PostgreSQL e modelo de geração do `.env` — e mede recuperação
e geração **separadas**. Recuperação ruim e geração ruim produzem o
mesmo sintoma, resposta errada, e pedem correções opostas (seção 5.1):
mexer em chunking, `k` e embeddings, ou mexer em prompt e modelo. Um
número único esconderia qual dos dois quebrou.

    python -m app.rag.bancada                        # conjunto inteiro
    python -m app.rag.bancada --ids R01 R24          # só alguns casos
    python -m app.rag.bancada --saida bancada.md     # + detalhe para revisão
    python -m app.rag.bancada --score-minimo 0       # calibração do corte

Indicadores:

| Indicador | O que mede | Meta |
|---|---|---|
| Recall@k | Os documentos esperados estão entre os `k` recuperados | ≥ 0,90 (5.1) |
| Abstenção correta | Recusa quando a resposta não está no corpus ou no escopo | ≥ 0,80 (5.1) |
| Acerto de conteúdo | Respondeu, com os termos esperados e sem os proibidos | ≥ 0,80, não pactuada |
| Vazamento | Trecho de projeto proibido recuperado, ou valor dele na resposta | zero |

**Fidelidade não é medida aqui.** "Nenhuma afirmação sem apoio no trecho
citado" pede leitura de quem conhece o corpus; um juiz automático seria
o mesmo tipo de modelo julgando a si mesmo. O que a bancada garante por
construção é que toda resposta entregue cita documentos que o modelo de
fato recebeu (`geracao.interpretar`), e o `--saida` escreve cada resposta
ao lado dos trechos citados, que é o material da revisão.

**O conjunto foi escrito antes da primeira medição** (seção 5.2) e não
deve ser ajustado ao que o sistema acerta: um caso que falha é
informação, não defeito do caso. Perguntas novas entram; as existentes
só mudam se o corpus mudar.

O gabarito das imperfeições plantadas na base não entra nem aqui nem na
pasta indexada: se o agente pudesse recuperá-lo, passaria a responder
lendo as respostas em vez dos dados.
"""

import argparse
import asyncio
import csv
import sys
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from app.config import settings
from app.rag.fluxo import FluxoRag, ResultadoRag
from app.rag.geracao import Situacao
from app.rag.linguagem.base import ErroGeracao
from app.rag.vetorial.base import Escopo
from app.schemas.usuario import Perfil

_MIDDLEWARE = Path(__file__).resolve().parents[2]
CAMINHO_CONJUNTO = _MIDDLEWARE / "dados" / "bancada-rag.csv"

META_RECALL = 0.90
META_ABSTENCAO = 0.80
META_ACERTO_CONTEUDO = 0.80  # não pactuada: a seção 5.1 não fixa meta de conteúdo

# Pausa entre casos. A camada gratuita do Gemini limita requisições por
# minuto, e o adaptador já repete o 429 — a pausa evita que a bancada
# gaste as novas tentativas de cada caso esperando a cota do anterior.
INTERVALO_PADRAO = 4.0


# --- conjunto de referência -------------------------------------------------


@dataclass(frozen=True)
class Caso:
    """Uma pergunta do conjunto de referência e o que conta como acerto.

    `documentos_esperados` e `deve_conter` são grupos: todos os grupos
    precisam ser satisfeitos, e dentro de cada grupo basta uma das
    alternativas. No CSV, `;` separa grupos e `|` separa alternativas —
    "IN-04-2023_NI;PRJ-2025-042_RSP_2026-08" pede os dois documentos;
    "PRJ-2025-042_RSP_2026-08|PORT-2026_PORTF" aceita qualquer um.
    """

    id: str
    caso: str
    intencao: str
    perfil: Perfil
    projetos: frozenset[str]
    pergunta: str
    espera_resposta: bool
    documentos_esperados: tuple[tuple[str, ...], ...]
    deve_conter: tuple[tuple[str, ...], ...]
    nao_deve_conter: tuple[str, ...]
    projetos_proibidos: frozenset[str]

    @property
    def escopo(self) -> Escopo:
        return Escopo(perfil=self.perfil, projetos=self.projetos)


def _grupos(campo: str) -> tuple[tuple[str, ...], ...]:
    grupos = (
        tuple(alternativa.strip() for alternativa in grupo.split("|") if alternativa.strip())
        for grupo in campo.split(";")
    )
    return tuple(grupo for grupo in grupos if grupo)


def _lista(campo: str, separador: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in campo.split(separador) if item.strip())


def carregar(caminho: Path = CAMINHO_CONJUNTO) -> list[Caso]:
    """Lê o conjunto de referência. Linha malformada falha nomeando o caso."""
    with caminho.open(encoding="utf-8", newline="") as arquivo:
        linhas = list(csv.DictReader(arquivo))

    casos = []
    for linha in linhas:
        try:
            caso = Caso(
                id=linha["id"],
                caso=linha["caso"],
                intencao=linha["intencao"],
                perfil=Perfil(linha["perfil"]),
                projetos=frozenset(_lista(linha["projetos"], ";")),
                pergunta=linha["pergunta"],
                espera_resposta=linha["espera_resposta"].strip().lower() == "sim",
                documentos_esperados=_grupos(linha["documentos_esperados"]),
                deve_conter=_grupos(linha["deve_conter"]),
                nao_deve_conter=_lista(linha["nao_deve_conter"], "|"),
                projetos_proibidos=frozenset(_lista(linha["projetos_proibidos"], ";")),
            )
        except (KeyError, ValueError) as erro:
            raise ValueError(f"caso {linha.get('id', '?')} malformado: {erro}") from erro
        if caso.espera_resposta and not caso.documentos_esperados:
            raise ValueError(f"caso {caso.id} espera resposta mas não declara documento esperado")
        casos.append(caso)
    return casos


# --- avaliação de um caso ---------------------------------------------------


def normalizar(texto: str) -> str:
    """Minúsculas, sem acento e com espaços simples — para comparar termos."""
    sem_acento = unicodedata.normalize("NFKD", texto)
    sem_acento = "".join(c for c in sem_acento if not unicodedata.combining(c))
    return " ".join(sem_acento.casefold().split())


def contem(texto: str, alternativas: Sequence[str]) -> bool:
    alvo = normalizar(texto)
    return any(normalizar(alternativa) in alvo for alternativa in alternativas)


@dataclass(frozen=True)
class Avaliacao:
    """O que aconteceu com um caso, já confrontado com o esperado."""

    caso: Caso
    situacao: Situacao | None  # None quando o modelo falhou
    texto: str
    documentos_recuperados: tuple[str, ...]
    score_topo: float | None
    # Fração dos grupos de documentos esperados presentes na recuperação;
    # None quando o caso não declara documento esperado.
    recall: float | None
    # Para os casos que esperam resposta: respondeu com o conteúdo certo.
    conteudo_ok: bool | None
    vazou: bool
    latencia_ms: int = 0
    erro: str | None = None
    resultado: ResultadoRag | None = None

    @property
    def respondeu(self) -> bool:
        return self.situacao is Situacao.RESPONDIDA

    @property
    def abstencao_correta(self) -> bool | None:
        if self.caso.espera_resposta or self.erro:
            return None
        return not self.respondeu


def avaliar_caso(caso: Caso, resultado: ResultadoRag) -> Avaliacao:
    resposta, recuperacao = resultado.resposta, resultado.recuperacao
    documentos = tuple(dict.fromkeys(t.documento_id for t in recuperacao.trechos))

    recall = None
    if caso.documentos_esperados:
        achados = sum(
            1 for grupo in caso.documentos_esperados if any(d in documentos for d in grupo)
        )
        recall = achados / len(caso.documentos_esperados)

    proibido_no_texto = resposta.respondida and contem(resposta.texto, caso.nao_deve_conter)
    conteudo_ok = None
    if caso.espera_resposta:
        conteudo_ok = (
            resposta.respondida
            and all(contem(resposta.texto, grupo) for grupo in caso.deve_conter)
            and not proibido_no_texto
        )

    projeto_proibido = any(t.projeto in caso.projetos_proibidos for t in recuperacao.trechos)
    vazou = projeto_proibido or (not caso.espera_resposta and proibido_no_texto)

    return Avaliacao(
        caso=caso,
        situacao=resposta.situacao,
        texto=resposta.texto,
        documentos_recuperados=documentos,
        score_topo=recuperacao.trechos[0].score if recuperacao.trechos else None,
        recall=recall,
        conteudo_ok=conteudo_ok,
        vazou=vazou,
        latencia_ms=resultado.latencia_ms,
        resultado=resultado,
    )


def falha(caso: Caso, erro: Exception) -> Avaliacao:
    """Caso em que o modelo não respondeu — contado à parte, não como erro do RAG."""
    return Avaliacao(
        caso=caso,
        situacao=None,
        texto="",
        documentos_recuperados=(),
        score_topo=None,
        recall=None,
        conteudo_ok=None,
        vazou=False,
        erro=str(erro),
    )


# --- resumo -----------------------------------------------------------------


@dataclass(frozen=True)
class Resumo:
    recall_medio: float | None
    abstencao_correta: float | None
    acerto_conteudo: float | None
    falsas_abstencoes: int
    nao_fundamentadas: int
    vazamentos: tuple[str, ...]
    falhas_do_modelo: tuple[str, ...]
    total: int


def _media(valores: Sequence[float]) -> float | None:
    return sum(valores) / len(valores) if valores else None


def resumir(avaliacoes: Sequence[Avaliacao]) -> Resumo:
    validas = [a for a in avaliacoes if a.erro is None]
    return Resumo(
        recall_medio=_media([a.recall for a in validas if a.recall is not None]),
        abstencao_correta=_media(
            [1.0 if a.abstencao_correta else 0.0 for a in validas if not a.caso.espera_resposta]
        ),
        acerto_conteudo=_media(
            [1.0 if a.conteudo_ok else 0.0 for a in validas if a.caso.espera_resposta]
        ),
        falsas_abstencoes=sum(1 for a in validas if a.caso.espera_resposta and not a.respondeu),
        nao_fundamentadas=sum(1 for a in validas if a.situacao is Situacao.NAO_FUNDAMENTADA),
        vazamentos=tuple(a.caso.id for a in validas if a.vazou),
        falhas_do_modelo=tuple(a.caso.id for a in avaliacoes if a.erro is not None),
        total=len(avaliacoes),
    )


# --- relatório --------------------------------------------------------------


def _linha(rotulo: str, valor: str) -> str:
    return f"  {rotulo:<34} {valor}"


def _meta(rotulo: str, medido: float | None, alvo: float, pactuada: bool = True) -> str:
    if medido is None:
        return _linha(rotulo, "sem casos")
    marca = "ATINGIDA " if medido >= alvo else "ABAIXO   "
    sufixo = "" if pactuada else "   (não pactuada)"
    return _linha(rotulo, f"{marca} alvo {alvo:.2f} · medido {medido:.3f}{sufixo}")


def _faixa(scores: Sequence[float]) -> str:
    if not scores:
        return "sem casos"
    return f"n={len(scores)} mín={min(scores):.3f} méd={_media(scores):.3f} máx={max(scores):.3f}"


def relatorio(avaliacoes: Sequence[Avaliacao], cabecalho: str = "") -> str:
    resumo = resumir(avaliacoes)
    partes = [cabecalho] if cabecalho else []

    partes.append("=== Metas da seção 5.1 ===")
    partes.append(_meta("recall@k", resumo.recall_medio, META_RECALL))
    partes.append(_meta("abstenção correta", resumo.abstencao_correta, META_ABSTENCAO))
    partes.append(
        _meta("acerto de conteúdo", resumo.acerto_conteudo, META_ACERTO_CONTEUDO, pactuada=False)
    )
    partes.append(
        _linha(
            "vazamento de permissão",
            "nenhum" if not resumo.vazamentos else "VAZOU em " + ", ".join(resumo.vazamentos),
        )
    )
    partes.append(_linha("abstenções indevidas", str(resumo.falsas_abstencoes)))
    partes.append(_linha("respostas sem citação válida", str(resumo.nao_fundamentadas)))
    if resumo.falhas_do_modelo:
        partes.append(
            _linha("modelo indisponível (fora da conta)", ", ".join(resumo.falhas_do_modelo))
        )

    partes.append("\n=== Por caso ===")
    for a in avaliacoes:
        if a.erro:
            partes.append(f"  {a.caso.id} {a.caso.caso:<11} FALHA DO MODELO  {a.erro}")
            continue
        esperado = "responder" if a.caso.espera_resposta else "abster"
        veredito = (
            ("ok" if a.conteudo_ok else "ERRO")
            if a.caso.espera_resposta
            else ("ok" if a.abstencao_correta else "ERRO")
        )
        if a.vazou:
            veredito = "VAZOU"
        recall = f"recall={a.recall:.2f}" if a.recall is not None else "recall=—   "
        topo = f"topo={a.score_topo:.3f}" if a.score_topo is not None else "topo=—    "
        partes.append(
            f"  {a.caso.id} {a.caso.caso:<11} {veredito:<5} esperado {esperado:<9} "
            f"{a.situacao.value if a.situacao else '—':<16} {recall} {topo} {a.latencia_ms} ms"
        )

    # Leitura para calibrar `rag_score_minimo`: se as faixas se separam, o
    # corte pode subir até o topo das não respondíveis sem custar recall.
    validas = [a for a in avaliacoes if a.erro is None and a.score_topo is not None]
    respondiveis = [a.score_topo for a in validas if a.caso.espera_resposta]
    nao_respondiveis = [a.score_topo for a in validas if not a.caso.espera_resposta]
    partes.append("\n=== Score do trecho mais similar (calibração do corte) ===")
    partes.append(_linha("casos que esperam resposta", _faixa(respondiveis)))
    partes.append(_linha("casos que esperam abstenção", _faixa(nao_respondiveis)))
    return "\n".join(partes)


def detalhe_markdown(avaliacoes: Sequence[Avaliacao]) -> str:
    """Cada resposta ao lado dos trechos citados — o material da revisão de fidelidade."""
    partes = ["# Bancada do RAG — respostas para revisão de fidelidade", ""]
    for a in avaliacoes:
        partes.append(f"## {a.caso.id} — {a.caso.pergunta}")
        partes.append("")
        partes.append(
            f"Perfil `{a.caso.perfil.value}`"
            + (f", projetos {', '.join(sorted(a.caso.projetos))}" if a.caso.projetos else "")
            + f" · situação `{a.situacao.value if a.situacao else 'falha do modelo'}`"
        )
        partes.append("")
        partes.append("> " + (a.texto or a.erro or "").replace("\n", "\n> "))
        partes.append("")
        if a.resultado is not None:
            for numero, fonte in enumerate(a.resultado.resposta.fontes, start=1):
                corpo = " ".join(fonte.trecho.split())
                partes.append(f"**[{numero}]** {fonte.documento} · {fonte.localizador}")
                partes.append("")
                partes.append(f"```text\n{corpo}\n```")
                partes.append("")
    return "\n".join(partes)


# --- execução ---------------------------------------------------------------


async def executar(
    fluxo: FluxoRag, casos: Sequence[Caso], intervalo: float = INTERVALO_PADRAO
) -> list[Avaliacao]:
    avaliacoes = []
    for posicao, caso in enumerate(casos):
        if posicao and intervalo > 0:
            await asyncio.sleep(intervalo)
        try:
            resultado = await fluxo.responder(caso.pergunta, caso.escopo)
        except ErroGeracao as erro:
            avaliacoes.append(falha(caso, erro))
            continue
        avaliacoes.append(avaliar_caso(caso, resultado))
    return avaliacoes


async def _rodar(casos: Sequence[Caso], intervalo: float) -> list[Avaliacao]:
    from app.persistence.sessao import encerrar, fabrica_de_sessoes
    from app.rag.fluxo import montar_fluxo

    try:
        async with fabrica_de_sessoes()() as sessao:
            return await executar(montar_fluxo(sessao), casos, intervalo)
    finally:
        await encerrar()


def main(argv: list[str] | None = None) -> int:
    # Console do Windows em cp1252 — mesmo tratamento das outras bancadas.
    for fluxo in (sys.stdout, sys.stderr):
        if hasattr(fluxo, "reconfigure"):
            fluxo.reconfigure(encoding="utf-8")

    analisador = argparse.ArgumentParser(
        prog="python -m app.rag.bancada",
        description="Mede recuperação e geração do RAG sobre o conjunto de referência.",
    )
    analisador.add_argument("--ids", nargs="*", default=[], help="roda só estes casos")
    analisador.add_argument("--saida", type=Path, help="escreve o detalhe em Markdown aqui")
    analisador.add_argument(
        "--intervalo", type=float, default=INTERVALO_PADRAO, help="segundos entre casos"
    )
    analisador.add_argument(
        "--score-minimo",
        type=float,
        help="sobrepõe RAG_SCORE_MINIMO nesta execução (0 para ver a distribuição inteira)",
    )
    argumentos = analisador.parse_args(argv)

    casos = carregar()
    if argumentos.ids:
        pedidos = set(argumentos.ids)
        casos = [caso for caso in casos if caso.id in pedidos]
    if argumentos.score_minimo is not None:
        settings.rag_score_minimo = argumentos.score_minimo

    cabecalho = (
        f"Bancada do RAG · {len(casos)} casos · namespace {settings.pinecone_namespace!r} · "
        f"modelo {settings.llm_backend}/{settings.gemini_modelo} · k={settings.rag_top_k} · "
        f"score_minimo={settings.rag_score_minimo}\n"
    )
    try:
        avaliacoes = asyncio.run(_rodar(casos, argumentos.intervalo))
    except RuntimeError as erro:
        print(f"erro: {erro}", file=sys.stderr)
        return 1

    print(relatorio(avaliacoes, cabecalho))
    if argumentos.saida:
        argumentos.saida.write_text(detalhe_markdown(avaliacoes), encoding="utf-8")
        print(f"\ndetalhe escrito em {argumentos.saida}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
