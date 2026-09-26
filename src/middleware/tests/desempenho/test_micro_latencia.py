"""Micro-medições dos saltos locais previstos no orçamento de 5.1.7.3."""

import asyncio

import httpx

from app.config import settings
from app.pipeline.guardas import saida
from app.pipeline.guardas.abuso import classificador as abuso
from app.pipeline.guardas.injecao import classificador as injecao
from app.pipeline.guardas.injecao import regras
from app.pipeline.intencao import preprocessamento


def _medir_async(benchmark, funcao, *argumentos, **opcoes) -> None:
    benchmark(lambda: asyncio.run(funcao(*argumentos, **opcoes)))


def _transporte_content_safety() -> httpx.MockTransport:
    return httpx.MockTransport(
        lambda _: httpx.Response(
            200,
            json={
                "userPromptAnalysis": {"attackDetected": False},
                "documentsAnalysis": [],
                "categoriesAnalysis": [
                    {"category": categoria, "severity": 0}
                    for categoria in abuso.CATEGORIAS
                ],
            },
        )
    )


def test_latencia_regra_injecao(benchmark) -> None:
    benchmark(regras.contem_padrao_suspeito, "Qual o status do projeto PRJ-2024-018?")


def test_latencia_preprocessamento(benchmark) -> None:
    benchmark(preprocessamento.preprocessar, "Qual o status do projeto PRJ-2024-018?")


def test_latencia_classificador_injecao(benchmark, monkeypatch) -> None:
    monkeypatch.setattr(settings, "content_safety_endpoint", "https://cs-teste.local/")
    monkeypatch.setattr(settings, "content_safety_key", "chave-de-teste")
    _medir_async(
        benchmark,
        injecao.classificar,
        "Qual o status do projeto PRJ-2024-018?",
        transporte=_transporte_content_safety(),
    )


def test_latencia_classificador_abuso(benchmark, monkeypatch) -> None:
    monkeypatch.setattr(settings, "content_safety_endpoint", "https://cs-teste.local/")
    monkeypatch.setattr(settings, "content_safety_key", "chave-de-teste")
    _medir_async(
        benchmark,
        abuso.classificar,
        "Qual o status do projeto PRJ-2024-018?",
        transporte=_transporte_content_safety(),
    )


def test_latencia_guarda_saida(benchmark, monkeypatch) -> None:
    monkeypatch.setattr(settings, "content_safety_endpoint", "https://cs-teste.local/")
    monkeypatch.setattr(settings, "content_safety_key", "chave-de-teste")
    _medir_async(
        benchmark,
        saida.verificar,
        "O projeto está em andamento.",
        "consultar_status_projeto",
        transporte=_transporte_content_safety(),
    )