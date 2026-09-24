"""Comportamentos de falha da inscrição do webhook do Google Drive."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.webhooks.drive import inscricao as modulo
from app.webhooks.drive.inscricao import InscricaoDrive
from app.webhooks.modelos import EstadoCanal


class _Sessao:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *_erro):
        return False


class _Canais:
    def __init__(self, _sessao):
        pass

    async def obter(self, _canal_id):
        return SimpleNamespace(estado=EstadoCanal.ATIVO, recurso_id="recurso-1")


async def test_falha_remota_ainda_encerra_canal_localmente(monkeypatch):
    monkeypatch.setattr(modulo, "CanalDriveRepository", _Canais)
    inscricao = InscricaoDrive(
        servico=None,
        fabrica_sessoes=lambda: _Sessao(),
        fonte_id="fonte-teste",
        url="https://exemplo.test/webhook",
        validade=modulo.timedelta(hours=1),
    )
    encerramento_local = AsyncMock()
    monkeypatch.setattr(inscricao, "_encerrar_registro", encerramento_local)

    def falhar_parada(_canal_id, _recurso_id):
        raise RuntimeError("503 do Google")

    monkeypatch.setattr(inscricao, "_parar", falhar_parada)

    with pytest.raises(RuntimeError, match="503 do Google"):
        await inscricao.encerrar("canal-1")

    encerramento_local.assert_awaited_once_with("canal-1")
