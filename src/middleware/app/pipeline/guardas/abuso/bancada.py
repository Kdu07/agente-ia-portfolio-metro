"""Bancada de calibração do limiar da guarda de abuso.

Consulta o Azure AI Content Safety uma única vez por enunciado e aplica
localmente cada limiar solicitado. Isso torna a comparação justa e evita
consumir a cota do serviço três vezes para obter os mesmos escores.

    python -m app.pipeline.guardas.abuso.bancada
    python -m app.pipeline.guardas.abuso.bancada --limiares 2 4 6
    python -m app.pipeline.guardas.abuso.bancada --saida resultado.md

Esta bancada calibra somente as categorias de conteúdo da guarda de abuso.
Prompt Shields e políticas corporativas têm contratos diferentes e não
entram nas taxas calculadas aqui.
"""

import argparse
import asyncio
import csv
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import httpx

from app.pipeline.guardas import content_safety
from app.pipeline.guardas.abuso.classificador import CATEGORIAS

_MIDDLEWARE = Path(__file__).resolve().parents[4]
CAMINHO_CONJUNTO = _MIDDLEWARE / "dados" / "bancada-content-safety.csv"
LIMIARES_PADRAO = (2, 4, 6)
INTERVALO_PADRAO = 0.25


@dataclass(frozen=True)
class Caso:
    """Enunciado rotulado antes da medição."""

    id: str
    texto: str
    esperado_bloqueio: bool
    categoria_esperada: str | None
    origem: str


@dataclass(frozen=True)
class Resultado:
    """Severidades brutas devolvidas pelo serviço para um caso."""

    caso: Caso
    severidades: dict[str, int]

    @property
    def severidade_maxima(self) -> int:
        return max(self.severidades.values(), default=0)

    @property
    def categoria_maxima(self) -> str | None:
        if not self.severidades:
            return None
        categoria = max(self.severidades, key=self.severidades.get)  # type: ignore[arg-type]
        return categoria if self.severidades[categoria] > 0 else None


@dataclass(frozen=True)
class Metricas:
    """Erros binários produzidos por um limiar."""

    limiar: int
    legitimos: int
    bloqueios_indevidos: int
    abusivos: int
    passagens_indevidas: int

    @property
    def taxa_bloqueio_indevido(self) -> float:
        return self.bloqueios_indevidos / self.legitimos if self.legitimos else 0.0

    @property
    def taxa_passagem_indevida(self) -> float:
        return self.passagens_indevidas / self.abusivos if self.abusivos else 0.0


def carregar(caminho: Path = CAMINHO_CONJUNTO) -> list[Caso]:
    """Carrega e valida o conjunto de referência."""
    with caminho.open(encoding="utf-8", newline="") as arquivo:
        linhas = list(csv.DictReader(arquivo))

    casos: list[Caso] = []
    ids: set[str] = set()
    for numero, linha in enumerate(linhas, start=2):
        identificador = (linha.get("id") or "").strip()
        texto = (linha.get("texto") or "").strip()
        esperado = (linha.get("esperado_bloqueio") or "").strip().casefold()
        categoria = (linha.get("categoria_esperada") or "").strip() or None
        origem = (linha.get("origem") or "").strip()

        if not identificador or identificador in ids:
            raise ValueError(f"linha {numero}: id ausente ou duplicado")
        if not texto or not origem:
            raise ValueError(f"caso {identificador}: texto e origem são obrigatórios")
        if esperado not in {"sim", "nao"}:
            raise ValueError(f"caso {identificador}: esperado_bloqueio deve ser sim ou nao")
        if categoria is not None and categoria not in CATEGORIAS:
            raise ValueError(f"caso {identificador}: categoria desconhecida {categoria!r}")
        if esperado == "sim" and categoria is None:
            raise ValueError(f"caso {identificador}: caso abusivo precisa de categoria esperada")
        if esperado == "nao" and categoria is not None:
            raise ValueError(f"caso {identificador}: caso legítimo não deve declarar categoria")

        ids.add(identificador)
        casos.append(
            Caso(
                id=identificador,
                texto=texto,
                esperado_bloqueio=esperado == "sim",
                categoria_esperada=categoria,
                origem=origem,
            )
        )

    if not casos or not any(c.esperado_bloqueio for c in casos):
        raise ValueError("o conjunto precisa conter casos abusivos")
    if not any(not c.esperado_bloqueio for c in casos):
        raise ValueError("o conjunto precisa conter casos legítimos")
    return casos


def medir(resultados: Sequence[Resultado], limiar: int) -> Metricas:
    """Calcula falsos bloqueios e falsas passagens para um limiar."""
    legitimos = [r for r in resultados if not r.caso.esperado_bloqueio]
    abusivos = [r for r in resultados if r.caso.esperado_bloqueio]
    return Metricas(
        limiar=limiar,
        legitimos=len(legitimos),
        bloqueios_indevidos=sum(r.severidade_maxima >= limiar for r in legitimos),
        abusivos=len(abusivos),
        passagens_indevidas=sum(r.severidade_maxima < limiar for r in abusivos),
    )


def _severidades(dados: dict, caso_id: str) -> dict[str, int]:
    analises = dados.get("categoriesAnalysis")
    if not isinstance(analises, list):
        raise content_safety.Indisponivel(f"caso {caso_id}: resposta sem categoriesAnalysis")

    resultado: dict[str, int] = {}
    for item in analises:
        if not isinstance(item, dict):
            raise content_safety.Indisponivel(f"caso {caso_id}: categoria malformada")
        categoria = item.get("category")
        severidade = item.get("severity")
        if categoria not in CATEGORIAS or not isinstance(severidade, int):
            raise content_safety.Indisponivel(f"caso {caso_id}: categoria ou severidade inválida")
        resultado[categoria] = severidade

    ausentes = set(CATEGORIAS) - resultado.keys()
    if ausentes:
        raise content_safety.Indisponivel(
            f"caso {caso_id}: categorias ausentes: {', '.join(sorted(ausentes))}"
        )
    return resultado


async def executar(
    casos: Sequence[Caso],
    intervalo: float = INTERVALO_PADRAO,
    *,
    transporte: httpx.AsyncBaseTransport | None = None,
) -> list[Resultado]:
    """Obtém os escores reais, interrompendo se qualquer caso falhar."""
    resultados: list[Resultado] = []
    async with content_safety.sessao(transporte) as servico:
        for posicao, caso in enumerate(casos):
            if posicao and intervalo > 0:
                await asyncio.sleep(intervalo)
            dados = await servico.analisar(
                "text:analyze",
                {
                    "text": caso.texto,
                    "categories": list(CATEGORIAS),
                    "outputType": "FourSeverityLevels",
                },
            )
            resultados.append(Resultado(caso, _severidades(dados, caso.id)))
    return resultados


def relatorio(resultados: Sequence[Resultado], limiares: Sequence[int]) -> str:
    """Gera evidência reproduzível com taxas e casos que erraram."""
    linhas = [
        "# Calibração do Azure AI Content Safety",
        "",
        (
            f"Conjunto: {len(resultados)} casos "
            f"({sum(not r.caso.esperado_bloqueio for r in resultados)} legítimos e "
            f"{sum(r.caso.esperado_bloqueio for r in resultados)} abusivos)."
        ),
        "",
        "| Limiar | Bloqueio indevido | Taxa | Passagem indevida | Taxa |",
        "|---:|---:|---:|---:|---:|",
    ]
    for limiar in limiares:
        metricas = medir(resultados, limiar)
        linhas.append(
            f"| {limiar} | {metricas.bloqueios_indevidos}/{metricas.legitimos} | "
            f"{metricas.taxa_bloqueio_indevido:.1%} | "
            f"{metricas.passagens_indevidas}/{metricas.abusivos} | "
            f"{metricas.taxa_passagem_indevida:.1%} |"
        )

    linhas += [
        "",
        "## Resultado por caso",
        "",
        "| ID | Esperado | Categoria | Severidade máxima |",
        "|---|---|---|---:|",
    ]
    for resultado in resultados:
        linhas.append(
            f"| {resultado.caso.id} | "
            f"{'bloquear' if resultado.caso.esperado_bloqueio else 'liberar'} | "
            f"{resultado.categoria_maxima or '—'} | {resultado.severidade_maxima} |"
        )
    return "\n".join(linhas)


def main(argv: list[str] | None = None) -> int:
    for fluxo in (sys.stdout, sys.stderr):
        if hasattr(fluxo, "reconfigure"):
            fluxo.reconfigure(encoding="utf-8")

    analisador = argparse.ArgumentParser(
        prog="python -m app.pipeline.guardas.abuso.bancada",
        description="Compara limiares da guarda de abuso no Azure AI Content Safety real.",
    )
    analisador.add_argument(
        "--limiares", nargs="+", type=int, default=list(LIMIARES_PADRAO), choices=(2, 4, 6)
    )
    analisador.add_argument("--intervalo", type=float, default=INTERVALO_PADRAO)
    analisador.add_argument("--conjunto", type=Path, default=CAMINHO_CONJUNTO)
    analisador.add_argument("--saida", type=Path)
    argumentos = analisador.parse_args(argv)

    if not content_safety.configurado():
        print("erro: configure CONTENT_SAFETY_ENDPOINT e CONTENT_SAFETY_KEY", file=sys.stderr)
        return 1

    try:
        resultados = asyncio.run(executar(carregar(argumentos.conjunto), argumentos.intervalo))
    except (OSError, ValueError, content_safety.Indisponivel) as erro:
        print(f"erro: {erro}", file=sys.stderr)
        return 1

    texto = relatorio(resultados, argumentos.limiares)
    print(texto)
    if argumentos.saida:
        argumentos.saida.write_text(texto + "\n", encoding="utf-8")
        print(f"\nresultado escrito em {argumentos.saida}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
