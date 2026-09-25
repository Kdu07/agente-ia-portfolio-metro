"""Rota GET /voz/token: sessão obrigatória e chave nunca exposta."""

from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.api import deps
from app.api.routes import voz
from app.config import settings
from app.main import app
from app.schemas.usuario import Perfil, UsuarioAutenticado
from app.voz.speech import ErroConfiguracaoSpeech, ErroTokenSpeech, TokenVoz

CHAVE = "chave-de-teste-que-nao-pode-vazar"


@pytest.fixture
def emitir(monkeypatch):
    monkeypatch.setattr(settings, "speech_key", CHAVE)
    emitir = AsyncMock(return_value=TokenVoz(token="eyJ.token.curto", regiao="brazilsouth"))
    monkeypatch.setattr(voz, "emitir_token", emitir)
    overrides = app.dependency_overrides.copy()
    overrides.pop(deps.obter_usuario_atual, None)
    # Sem cookie, a dependência real de autenticação responde 401 antes do banco.
    overrides[deps.obter_sessao] = lambda: None
    monkeypatch.setattr(app, "dependency_overrides", overrides)
    return emitir


@pytest.fixture
def sem_sessao(emitir):
    with TestClient(app) as cliente:
        yield cliente


@pytest.fixture
def com_sessao(sem_sessao, monkeypatch):
    usuario = UsuarioAutenticado(id="u-teste-voz", nome="Teste", perfil=Perfil.MEMBRO_EQUIPE)
    monkeypatch.setitem(app.dependency_overrides, deps.obter_usuario_atual, lambda: usuario)
    return sem_sessao


def test_sessao_valida_recebe_token_curto_sem_a_chave(com_sessao, emitir):
    resposta = com_sessao.get("/voz/token")

    assert resposta.status_code == 200
    assert resposta.json() == {
        "token": "eyJ.token.curto",
        "regiao": "brazilsouth",
        "expira_em_segundos": 600,
        "idioma": "pt-BR",
    }
    assert resposta.headers["Cache-Control"] == "no-store"
    assert CHAVE not in resposta.text
    emitir.assert_awaited_once()


def test_sem_sessao_responde_401_sem_emitir(sem_sessao, emitir):
    resposta = sem_sessao.get("/voz/token")

    assert resposta.status_code == 401
    emitir.assert_not_awaited()


@pytest.mark.parametrize(
    "falha",
    [
        ErroConfiguracaoSpeech("SPEECH_KEY não configurada"),
        ErroTokenSpeech("Serviço respondeu 401"),
    ],
)
def test_falha_na_emissao_responde_503_generico(com_sessao, emitir, falha):
    emitir.side_effect = falha

    resposta = com_sessao.get("/voz/token")

    assert resposta.status_code == 503
    assert resposta.json() == {
        "detail": "Entrada por voz indisponível no momento. Digite a mensagem."
    }
    assert "SPEECH_KEY" not in resposta.text and "401" not in resposta.text
