"""Testes das contas e do contrato da bancada de Content Safety."""

import csv
from pathlib import Path

import httpx
import pytest

from app.config import settings
from app.pipeline.guardas.abuso import bancada
from app.pipeline.guardas.abuso.bancada import Caso, Resultado


def caso(identificador: str, esperado: bool) -> Caso:
    return Caso(
        id=identificador,
        texto="texto de teste",
        esperado_bloqueio=esperado,
        categoria_esperada="Hate" if esperado else None,
        origem="teste",
    )


def resultado(identificador: str, esperado: bool, severidade: int) -> Resultado:
    return Resultado(
        caso(identificador, esperado),
        {"Hate": severidade, "SelfHarm": 0, "Sexual": 0, "Violence": 0},
    )


def test_conjunto_versionado_tem_duas_classes_e_quatro_categorias() -> None:
    casos = bancada.carregar()

    assert any(c.esperado_bloqueio for c in casos)
    assert any(not c.esperado_bloqueio for c in casos)
    assert {c.categoria_esperada for c in casos if c.esperado_bloqueio} == {
        "Hate",
        "SelfHarm",
        "Sexual",
        "Violence",
    }


def test_metricas_distinguem_os_dois_tipos_de_erro() -> None:
    resultados = [
        resultado("L1", False, 0),
        resultado("L2", False, 2),
        resultado("A1", True, 6),
        resultado("A2", True, 0),
    ]

    metricas = bancada.medir(resultados, limiar=2)

    assert metricas.bloqueios_indevidos == 1
    assert metricas.taxa_bloqueio_indevido == 0.5
    assert metricas.passagens_indevidas == 1
    assert metricas.taxa_passagem_indevida == 0.5


def test_relatorio_compara_tres_limiares() -> None:
    resultados = [resultado("L1", False, 0), resultado("A1", True, 4)]

    texto = bancada.relatorio(resultados, (2, 4, 6))

    assert "| 2 | 0/1 | 0.0% | 0/1 | 0.0% |" in texto
    assert "| 4 | 0/1 | 0.0% | 0/1 | 0.0% |" in texto
    assert "| 6 | 0/1 | 0.0% | 1/1 | 100.0% |" in texto


def test_resultado_sem_severidade_nao_inventa_categoria() -> None:
    medicao = resultado("L1", False, 0)

    assert medicao.categoria_maxima is None


async def test_executar_consulta_cada_caso_uma_vez(monkeypatch: pytest.MonkeyPatch) -> None:
    # Sem o endpoint, a URL fica relativa e o httpx a recusa antes do
    # transporte. Fixá-lo aqui tira o teste da dependência do `.env` local.
    monkeypatch.setattr(settings, "content_safety_endpoint", "https://content-safety.teste")
    chamadas: list[httpx.Request] = []

    def responder(request: httpx.Request) -> httpx.Response:
        chamadas.append(request)
        return httpx.Response(
            200,
            json={
                "categoriesAnalysis": [
                    {"category": categoria, "severity": 0}
                    for categoria in ("Hate", "SelfHarm", "Sexual", "Violence")
                ]
            },
        )

    casos = [caso("T1", False), caso("T2", False)]
    resultados = await bancada.executar(
        casos, intervalo=0, transporte=httpx.MockTransport(responder)
    )

    assert len(resultados) == 2
    assert len(chamadas) == 2
    assert all(chamada.url.path == "/contentsafety/text:analyze" for chamada in chamadas)


def test_carregar_rejeita_caso_abusivo_sem_categoria(tmp_path: Path) -> None:
    caminho = tmp_path / "casos.csv"
    with caminho.open("w", encoding="utf-8", newline="") as arquivo:
        escritor = csv.writer(arquivo)
        escritor.writerow(["id", "esperado_bloqueio", "categoria_esperada", "origem", "texto"])
        escritor.writerow(["A1", "sim", "", "teste", "texto"])
        escritor.writerow(["L1", "nao", "", "teste", "texto limpo"])

    with pytest.raises(ValueError, match="precisa de categoria"):
        bancada.carregar(caminho)
