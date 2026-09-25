"""Testes da configuração de logs da API (app/main.py)."""

import logging

import pytest

from app.main import configurar_logs


@pytest.fixture
def nome_logger():
    # Um logger próprio por teste: mexer no `app` de verdade mudaria o
    # nível e os handlers vistos pelos outros testes do processo.
    nome = "teste_configurar_logs"
    yield nome
    logger = logging.getLogger(nome)
    for manipulador in list(logger.handlers):
        logger.removeHandler(manipulador)
    logger.setLevel(logging.NOTSET)


def test_liga_info_com_um_handler(nome_logger):
    configurar_logs(nome_logger)

    logger = logging.getLogger(nome_logger)
    assert logger.level == logging.INFO
    assert len(logger.handlers) == 1


def test_e_idempotente(nome_logger):
    configurar_logs(nome_logger)
    configurar_logs(nome_logger)

    assert len(logging.getLogger(nome_logger).handlers) == 1


def test_info_de_submodulo_chega_ao_stderr(nome_logger, capsys):
    """O caso que motivou a configuração: o INFO de `app.rag.fluxo`."""
    configurar_logs(nome_logger)

    logging.getLogger(f"{nome_logger}.rag.fluxo").info("RAG situacao=%s", "sem_evidencia")

    assert "RAG situacao=sem_evidencia" in capsys.readouterr().err


def test_api_configura_o_pacote_app():
    assert logging.getLogger("app").getEffectiveLevel() == logging.INFO
    assert logging.getLogger("app").handlers
