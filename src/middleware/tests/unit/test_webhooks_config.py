import base64
import hmac
import json
import traceback
from pathlib import Path

import pytest

from app.auth.webhooks import WebhookRecusado, verificar_portfolio
from app.auth.webhooks_config import ErroConfiguracaoWebhook, carregar_chaves_portfolio
from app.config import Settings

SEGREDO = bytes(range(32))


def registro(**alteracoes):
    return {
        "source_id": "portfolio",
        "key_id": "k1",
        "segredo_base64": base64.b64encode(SEGREDO).decode(),
        "valida_desde": 1000,
        "valida_ate": 3000,
        "revogada": False,
        **alteracoes,
    }


def autenticar(chaves, *, chave_id="k1", segredo=SEGREDO, agora=2000):
    corpo = b'{"source_id":"portfolio"}'
    assinatura = hmac.digest(segredo, f"portfolio\n{chave_id}\n2000\n".encode() + corpo, "sha256")
    return verificar_portfolio(
        [
            (b"x-prata-source", b"portfolio"),
            (b"x-prata-key-id", chave_id.encode()),
            (b"x-prata-timestamp", b"2000"),
            (b"x-prata-signature", base64.b64encode(assinatura)),
        ],
        corpo,
        chaves,
        agora=agora,
    )


def test_configuracao_do_ambiente_chega_ao_validador(tmp_path, monkeypatch):
    caminho = tmp_path / "chaves.json"
    caminho.write_text(json.dumps([registro()]), encoding="utf-8")
    monkeypatch.setenv("WEBHOOK_PORTFOLIO_CHAVES_ARQUIVO", str(caminho))
    configuracao = Settings(_env_file=None)
    chaves = carregar_chaves_portfolio(configuracao.webhook_portfolio_chaves_arquivo)
    assert autenticar(chaves) == "portfolio"
    assert SEGREDO.hex() not in repr(chaves)
    assert registro()["segredo_base64"] not in repr(chaves)


def test_rotacao_revogacao_e_remocao_refletem_no_proximo_carregamento(tmp_path):
    caminho = tmp_path / "chaves.json"
    novo_segredo = b"n" * 32
    novo = registro(key_id="k2", segredo_base64=base64.b64encode(novo_segredo).decode())
    caminho.write_text(json.dumps([registro(), novo]), encoding="utf-8")
    chaves = carregar_chaves_portfolio(caminho)
    assert autenticar(chaves) == "portfolio"
    assert autenticar(chaves, chave_id="k2", segredo=novo_segredo) == "portfolio"

    caminho.write_text(json.dumps([registro(revogada=True), novo]), encoding="utf-8")
    chaves = carregar_chaves_portfolio(caminho)
    with pytest.raises(WebhookRecusado) as erro:
        autenticar(chaves)
    assert erro.value.status == 401
    assert autenticar(chaves, chave_id="k2", segredo=novo_segredo) == "portfolio"

    caminho.write_text("[]", encoding="utf-8")
    with pytest.raises(WebhookRecusado) as erro:
        autenticar(carregar_chaves_portfolio(caminho), chave_id="k2", segredo=novo_segredo)
    assert erro.value.status == 401


@pytest.mark.parametrize(
    "alteracoes",
    [
        {"segredo_base64": "!segredo-sintetico!"},
        {"segredo_base64": base64.b64encode(b"curto").decode()},
        {"segredo_base64": base64.b64encode(SEGREDO).decode() + "\n"},
        {"source_id": "fonte invalida"},
        {"key_id": "x" * 65},
        {"valida_desde": "1000"},
        {"valida_desde": True},
        {"valida_desde": -1},
        {"valida_ate": 1000},
        {"revogada": "false"},
        {"campo_desconhecido": "valor"},
    ],
)
def test_cadastro_invalido_nao_expoe_segredo(tmp_path, alteracoes):
    caminho = tmp_path / "chaves.json"
    invalido = registro(**alteracoes)
    caminho.write_text(json.dumps([registro(key_id="valida"), invalido]), encoding="utf-8")
    with pytest.raises(ErroConfiguracaoWebhook) as erro:
        carregar_chaves_portfolio(caminho)
    saida = "".join(traceback.format_exception(erro.value))
    assert invalido["segredo_base64"] not in saida
    assert registro()["segredo_base64"] not in saida


@pytest.mark.parametrize(
    "conteudo",
    [
        "{",
        "null",
        "{}",
        '[{"source_id":"a","source_id":"b"}]',
        json.dumps([registro(), registro()]),
        json.dumps([{k: v for k, v in registro().items() if k != "segredo_base64"}]),
    ],
)
def test_recusa_formato_campos_repetidos_e_identificadores_duplicados(tmp_path, conteudo):
    caminho = tmp_path / "chaves.json"
    caminho.write_text(conteudo, encoding="utf-8")
    with pytest.raises(ErroConfiguracaoWebhook):
        carregar_chaves_portfolio(caminho)


def test_falha_de_leitura_nao_reutiliza_chaves_antigas(tmp_path):
    caminho = tmp_path / "chaves.json"
    caminho.write_text(json.dumps([registro()]), encoding="utf-8")
    assert autenticar(carregar_chaves_portfolio(caminho)) == "portfolio"
    caminho.unlink()
    with pytest.raises(ErroConfiguracaoWebhook):
        carregar_chaves_portfolio(caminho)


def test_caminho_vazio_e_invalido():
    with pytest.raises(ErroConfiguracaoWebhook):
        carregar_chaves_portfolio("")


def test_env_example_inicia_sem_habilitar_autenticacao(monkeypatch):
    monkeypatch.delenv("WEBHOOK_PORTFOLIO_CHAVES_ARQUIVO", raising=False)
    exemplo = Path(__file__).resolve().parents[2] / ".env.example"
    configuracao = Settings(_env_file=exemplo)
    assert configuracao.webhook_portfolio_chaves_arquivo == ""
    with pytest.raises(ErroConfiguracaoWebhook):
        carregar_chaves_portfolio(configuracao.webhook_portfolio_chaves_arquivo)
