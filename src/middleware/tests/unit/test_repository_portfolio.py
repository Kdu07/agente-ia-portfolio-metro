"""Contratos dos repositórios do portfólio que não exigem PostgreSQL."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.persistence.repository_portfolio import UsuarioProjetoRepository


class _ResultadoEscalar:
    def __init__(self, valores: list[str]) -> None:
        self._valores = valores

    def scalars(self):
        return iter(self._valores)


@pytest.mark.asyncio
async def test_lista_codigos_de_projeto_inteiros() -> None:
    sessao = MagicMock()
    sessao.execute = AsyncMock(return_value=_ResultadoEscalar(["PRJ-2024-018", "PRJ-2025-042"]))

    codigos = await UsuarioProjetoRepository(sessao).listar_projetos_do_usuario("usuario-1")

    assert codigos == ["PRJ-2024-018", "PRJ-2025-042"]


@pytest.mark.asyncio
async def test_lista_ids_de_usuario_inteiros() -> None:
    sessao = MagicMock()
    sessao.execute = AsyncMock(return_value=_ResultadoEscalar(["usuario-123", "usuario-456"]))

    usuarios = await UsuarioProjetoRepository(sessao).listar_usuarios_do_projeto("PRJ-2024-018")

    assert usuarios == ["usuario-123", "usuario-456"]
