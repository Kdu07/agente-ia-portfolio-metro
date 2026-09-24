"""Testes das rotas de saúde e do aquecimento do classificador."""

from concurrent.futures import Future

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.pipeline.intencao import classificador


@pytest.fixture
def cliente():
    # Sem `with`: o lifespan não roda, e cada teste monta o estado do
    # aquecimento que quer observar.
    yield TestClient(app)
    app.state.aquecimento = None


def _aquecimento(*, resultado=None, erro: Exception | None = None, pendente=False) -> Future:
    futuro: Future = Future()
    if pendente:
        return futuro
    if erro is not None:
        futuro.set_exception(erro)
    else:
        futuro.set_result(resultado)
    return futuro


def test_health_responde_mesmo_durante_o_aquecimento(cliente):
    app.state.aquecimento = _aquecimento(pendente=True)

    resposta = cliente.get("/health")

    assert resposta.status_code == 200
    assert resposta.json() == {"status": "ok"}


def test_pronto_sem_aquecimento_configurado(cliente):
    app.state.aquecimento = None

    resposta = cliente.get("/health/pronto")

    assert resposta.status_code == 200
    assert resposta.json() == {"status": "pronto"}


def test_pronto_responde_503_enquanto_aquece(cliente):
    app.state.aquecimento = _aquecimento(pendente=True)

    resposta = cliente.get("/health/pronto")

    assert resposta.status_code == 503
    assert resposta.json() == {"status": "aquecendo"}


def test_pronto_depois_do_aquecimento(cliente):
    app.state.aquecimento = _aquecimento()

    resposta = cliente.get("/health/pronto")

    assert resposta.status_code == 200
    assert resposta.json() == {"status": "pronto"}


def test_pronto_responde_503_quando_o_aquecimento_falha(cliente):
    app.state.aquecimento = _aquecimento(erro=FileNotFoundError("classificador.joblib"))

    resposta = cliente.get("/health/pronto")

    assert resposta.status_code == 503
    assert resposta.json() == {"status": "falhou"}


def test_aquecer_faz_uma_classificacao_descartavel(monkeypatch):
    textos: list[str] = []
    monkeypatch.setattr(
        classificador,
        "_classificar_sincrono",
        lambda texto: textos.append(texto),
    )

    classificador.aquecer()

    assert len(textos) == 1


def test_aquecer_propaga_a_falha(monkeypatch):
    def falhar(texto):
        raise FileNotFoundError("classificador.joblib")

    monkeypatch.setattr(classificador, "_classificar_sincrono", falhar)

    with pytest.raises(FileNotFoundError):
        classificador.aquecer()
