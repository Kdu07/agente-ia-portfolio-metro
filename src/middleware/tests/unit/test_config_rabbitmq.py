import os
from pathlib import Path
from urllib.parse import unquote, urlsplit

import pytest
from pydantic import ValidationError

from app.config import Settings


@pytest.fixture(autouse=True)
def limpar_ambiente_rabbitmq(monkeypatch):
    for nome in tuple(os.environ):
        if nome.upper().startswith("RABBITMQ_"):
            monkeypatch.delenv(nome)


def test_env_example_carrega_conexao_local_e_limites():
    exemplo = Path(__file__).resolve().parents[2] / ".env.example"
    configuracao = Settings(_env_file=exemplo)
    url = urlsplit(configuracao.rabbitmq_url.get_secret_value())
    assert (url.hostname, url.port, url.path) == ("localhost", 5672, "/prata")
    assert configuracao.rabbitmq_exchange == "prata.events"
    assert configuracao.rabbitmq_dead_letter_exchange == "prata.dead-letter"
    assert configuracao.rabbitmq_prefetch_count == 10
    assert 1 + configuracao.rabbitmq_max_retries == 3


def test_componentes_do_ambiente_preservam_caracteres_especiais(monkeypatch):
    monkeypatch.setenv("RABBITMQ_HOST", "rabbitmq")
    monkeypatch.setenv("RABBITMQ_PORT", "5672")
    monkeypatch.setenv("RABBITMQ_USER", "usuario@local")
    monkeypatch.setenv("RABBITMQ_PASSWORD", "senha@:/#%?teste")
    monkeypatch.setenv("RABBITMQ_VHOST", "portfolio/teste")
    configuracao = Settings(_env_file=None)
    url = urlsplit(configuracao.rabbitmq_url.get_secret_value())
    assert (url.hostname, url.port) == ("rabbitmq", 5672)
    assert unquote(url.username) == "usuario@local"
    assert unquote(url.password) == "senha@:/#%?teste"
    assert unquote(url.path[1:]) == "portfolio/teste"
    assert "senha@:/#%?teste" not in repr(configuracao)
    assert configuracao.rabbitmq_url.get_secret_value() not in configuracao.model_dump_json()


def test_url_explicita_tem_prioridade_e_preserva_tls(monkeypatch):
    explicita = "amqps://emissor:senha%40teste@broker.example:5671/projetos?heartbeat=30"
    monkeypatch.setenv("RABBITMQ_URL", explicita)
    monkeypatch.setenv("RABBITMQ_HOST", "rabbitmq")
    configuracao = Settings(_env_file=None)
    assert configuracao.rabbitmq_url.get_secret_value() == explicita
    assert explicita not in repr(configuracao)
    assert explicita not in configuracao.model_dump_json()


@pytest.mark.parametrize("url", ["http://broker.example", "amqp://", "invalida"])
def test_recusa_url_sem_host_ou_protocolo_amqp(url):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, rabbitmq_url=url)


def test_erro_de_url_nao_expoe_credenciais():
    segredo = "segredo-sintetico-392"
    with pytest.raises(ValidationError) as erro:
        Settings(_env_file=None, rabbitmq_url=f"http://emissor:{segredo}@broker.example")
    assert segredo not in str(erro.value)


@pytest.mark.parametrize("campo,valor", [
    ("rabbitmq_port", 0),
    ("rabbitmq_port", 65536),
    ("rabbitmq_prefetch_count", 0),
    ("rabbitmq_prefetch_count", 65536),
    ("rabbitmq_max_retries", -1),
    ("rabbitmq_exchange", ""),
    ("rabbitmq_dead_letter_exchange", ""),
    ("rabbitmq_password", ""),
])
def test_recusa_configuracao_fora_dos_limites(campo, valor):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **{campo: valor})


def test_permite_desabilitar_retentativas():
    assert Settings(_env_file=None, rabbitmq_max_retries=0).rabbitmq_max_retries == 0
