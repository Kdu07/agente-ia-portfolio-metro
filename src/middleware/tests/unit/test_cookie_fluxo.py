"""Testes do cookie assinado que leva o fluxo de login até o callback."""

import pytest
from itsdangerous import URLSafeTimedSerializer

from app.auth import sessao
from app.auth.entra import ConfiguracaoAusente, FluxoPendente
from app.config import settings

FLUXO = FluxoPendente(estado="estado-1", code_verifier="verifier-1", nonce="nonce-1")


@pytest.fixture(autouse=True)
def segredo(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "session_secret", "segredo-de-teste")


def test_ida_e_volta() -> None:
    assert sessao.ler_fluxo(sessao.assinar_fluxo(FLUXO)) == FLUXO


@pytest.mark.parametrize("valor", [None, "", "lixo", "a.b.c"])
def test_valor_invalido_vira_none(valor: str | None) -> None:
    assert sessao.ler_fluxo(valor) is None


def test_cookie_adulterado_vira_none() -> None:
    valor = sessao.assinar_fluxo(FLUXO)
    # Troca no payload, e não no fim da assinatura: o último caractere
    # base64 pode carregar só bits de preenchimento e decodificar igual.
    adulterado = ("A" if valor[0] != "A" else "B") + valor[1:]
    assert sessao.ler_fluxo(adulterado) is None


def test_cookie_assinado_com_outro_segredo_vira_none(monkeypatch: pytest.MonkeyPatch) -> None:
    valor = sessao.assinar_fluxo(FLUXO)
    monkeypatch.setattr(settings, "session_secret", "segredo-rotacionado")
    assert sessao.ler_fluxo(valor) is None


def test_cookie_de_sessao_nao_passa_por_cookie_de_fluxo() -> None:
    """Os salts separam os dois cookies, embora usem o mesmo segredo."""
    de_sessao = URLSafeTimedSerializer("segredo-de-teste", salt="sessao").dumps(
        {"estado": "e", "verifier": "v", "nonce": "n"}
    )
    assert sessao.ler_fluxo(de_sessao) is None


def test_fluxo_vencido_vira_none(monkeypatch: pytest.MonkeyPatch) -> None:
    valor = sessao.assinar_fluxo(FLUXO)
    monkeypatch.setattr(sessao, "DURACAO_FLUXO_SEGUNDOS", -1)
    assert sessao.ler_fluxo(valor) is None


def test_sem_segredo_nao_assina(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "session_secret", "")
    with pytest.raises(ConfiguracaoAusente):
        sessao.assinar_fluxo(FLUXO)
