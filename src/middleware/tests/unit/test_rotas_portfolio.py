"""Comportamento das rotas de portfólio sem depender do PostgreSQL.

Os repositórios são dublados na fronteira das rotas para verificar o que o
cliente observa: dados devolvidos, filtro de escopo e recusas de autorização.
"""

from datetime import UTC, date
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from app.api.routes import portfolio
from app.persistence.models import Indicador, Marco, PapelProjeto, Projeto, Risco
from app.schemas.usuario import Perfil, UsuarioAutenticado

CODIGO = "PRJ-2026-001"


def _usuario(
    perfil: Perfil = Perfil.LIDER_PROJETO,
    projetos: frozenset[str] = frozenset({CODIGO}),
) -> UsuarioAutenticado:
    return UsuarioAutenticado("usuario-1", "Usuário", perfil, projetos=projetos)


def _repositorio(**metodos):
    return SimpleNamespace(
        **{nome: AsyncMock(return_value=retorno) for nome, retorno in metodos.items()}
    )


@pytest.mark.asyncio
async def test_diretoria_lista_todo_o_portfolio() -> None:
    projetos = [Projeto(CODIGO, "Linha de teste")]
    repositorio = _repositorio(listar_todos=projetos, listar_por_usuario=[])

    resposta = await portfolio.listar_projetos(_usuario(Perfil.DIRETORIA), None, repositorio)

    assert resposta == projetos
    repositorio.listar_todos.assert_awaited_once_with()
    repositorio.listar_por_usuario.assert_not_awaited()


@pytest.mark.asyncio
async def test_usuario_lista_somente_os_projetos_vinculados() -> None:
    projetos = [Projeto(CODIGO, "Linha de teste")]
    repositorio = _repositorio(listar_todos=[], listar_por_usuario=projetos)

    resposta = await portfolio.listar_projetos(_usuario(), None, repositorio)

    assert resposta == projetos
    repositorio.listar_por_usuario.assert_awaited_once_with("usuario-1")
    repositorio.listar_todos.assert_not_awaited()


@pytest.mark.asyncio
async def test_obter_projeto_devolve_o_registro_visivel() -> None:
    projeto = Projeto(CODIGO, "Linha de teste")
    repositorio = _repositorio(obter=projeto)

    assert await portfolio.obter_projeto(CODIGO, _usuario(), repositorio) is projeto
    repositorio.obter.assert_awaited_once_with(CODIGO)


@pytest.mark.asyncio
async def test_obter_projeto_recusa_consulta_fora_do_escopo() -> None:
    repositorio = _repositorio(obter=Projeto(CODIGO, "Linha de teste"))

    with pytest.raises(HTTPException) as erro:
        await portfolio.obter_projeto(CODIGO, _usuario(projetos=frozenset()), repositorio)

    assert erro.value.status_code == 403
    repositorio.obter.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("funcao", "item"),
    [
        (portfolio.listar_riscos, Risco("RIS-1", CODIGO, "Atraso")),
        (portfolio.listar_marcos, Marco("MAR-1", CODIGO, "Entrega", date(2026, 10, 1))),
        (portfolio.listar_indicadores, Indicador("IND-1", CODIGO, "Avanço")),
    ],
)
async def test_dimensoes_do_portfolio_respeitam_o_projeto(funcao, item) -> None:
    repositorio = _repositorio(listar_por_projeto=[item])

    resposta = await funcao(CODIGO, _usuario(), repositorio)

    assert resposta == [item]
    repositorio.listar_por_projeto.assert_awaited_once_with(CODIGO)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "funcao",
    [portfolio.listar_riscos, portfolio.listar_marcos, portfolio.listar_indicadores],
)
async def test_dimensoes_recusam_projeto_fora_do_escopo(funcao) -> None:
    repositorio = _repositorio(listar_por_projeto=[])

    with pytest.raises(HTTPException) as erro:
        await funcao(CODIGO, _usuario(projetos=frozenset()), repositorio)

    assert erro.value.status_code == 403
    repositorio.listar_por_projeto.assert_not_awaited()


@pytest.mark.asyncio
async def test_marcos_vencendo_sao_filtrados_pelo_escopo_do_usuario() -> None:
    visivel = Marco("MAR-1", CODIGO, "Entrega", date(2026, 10, 1))
    oculto = Marco("MAR-2", "PRJ-OUTRO", "Entrega", date(2026, 10, 2))
    repositorio = _repositorio(listar_vencendo=[visivel, oculto])

    resposta = await portfolio.listar_marcos_vencendo(_usuario(), repositorio, dias=14)

    assert resposta == [visivel]
    repositorio.listar_vencendo.assert_awaited_once_with(14)


@pytest.mark.asyncio
async def test_lista_usuarios_do_projeto_visivel() -> None:
    repositorio = _repositorio(listar_usuarios_do_projeto=["usuario-2"])

    resposta = await portfolio.listar_usuarios_projeto(CODIGO, _usuario(), repositorio)

    assert resposta == ["usuario-2"]
    repositorio.listar_usuarios_do_projeto.assert_awaited_once_with(CODIGO)


@pytest.mark.asyncio
async def test_adiciona_usuario_com_papel_e_data_utc() -> None:
    repositorio = _repositorio(adicionar=None)

    resposta = await portfolio.adicionar_usuario_projeto(
        CODIGO,
        "usuario-2",
        PapelProjeto.OBSERVADOR,
        _usuario(),
        repositorio,
    )

    assert resposta.usuario_id == "usuario-2"
    assert resposta.projeto_codigo == CODIGO
    assert resposta.papel == PapelProjeto.OBSERVADOR.value
    assert resposta.criado_em.tzinfo is UTC
    repositorio.adicionar.assert_awaited_once_with(resposta)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "usuario",
    [
        _usuario(Perfil.MEMBRO_EQUIPE),
        _usuario(Perfil.LIDER_PROJETO, projetos=frozenset()),
    ],
)
async def test_adicionar_usuario_recusa_permissao_ou_escopo(usuario) -> None:
    repositorio = _repositorio(adicionar=None)

    with pytest.raises(HTTPException) as erro:
        await portfolio.adicionar_usuario_projeto(
            CODIGO, "usuario-2", PapelProjeto.MEMBRO, usuario, repositorio
        )

    assert erro.value.status_code == 403
    repositorio.adicionar.assert_not_awaited()


@pytest.mark.asyncio
async def test_remove_usuario_do_projeto_visivel() -> None:
    repositorio = _repositorio(remover=None)

    resposta = await portfolio.remover_usuario_projeto(CODIGO, "usuario-2", _usuario(), repositorio)

    assert resposta is None
    repositorio.remover.assert_awaited_once_with("usuario-2", CODIGO)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "usuario",
    [
        _usuario(Perfil.MEMBRO_EQUIPE),
        _usuario(Perfil.LIDER_PROJETO, projetos=frozenset()),
    ],
)
async def test_remover_usuario_recusa_permissao_ou_escopo(usuario) -> None:
    repositorio = _repositorio(remover=None)

    with pytest.raises(HTTPException) as erro:
        await portfolio.remover_usuario_projeto(CODIGO, "usuario-2", usuario, repositorio)

    assert erro.value.status_code == 403
    repositorio.remover.assert_not_awaited()
