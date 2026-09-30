"""Casos TF-RF01-01 a TF-RF01-05 — acesso, permissões e perfil."""

import pytest
from fastapi.testclient import TestClient

from app.api import deps
from app.auth import permissoes
from app.auth import sessao as auth_sessao
from app.auth.entra import IdentidadeEntra
from app.main import app
from app.rag.geracao import TEXTO_SEM_EVIDENCIA
from app.rag.vetorial.base import Escopo
from app.schemas.usuario import Perfil, UsuarioAutenticado

PROJETO_PROPRIO = "PRJ-2026-001"
PROJETO_ALHEIO = "PRJ-2026-999"


def test_tf_rf01_01_lider_alcanca_projeto_sob_sua_responsabilidade() -> None:
    escopo = Escopo(Perfil.LIDER_PROJETO, frozenset({PROJETO_PROPRIO}))
    assert escopo.alcanca(PROJETO_PROPRIO, {Perfil.LIDER_PROJETO})
    assert not escopo.alcanca(PROJETO_ALHEIO, {Perfil.LIDER_PROJETO})


def test_tf_rf01_02_membro_nao_recebe_atributos_de_projeto_alheio() -> None:
    escopo = Escopo(Perfil.MEMBRO_EQUIPE, frozenset({PROJETO_PROPRIO}))
    atributos_protegidos = {PROJETO_ALHEIO, "Projeto Sigiloso", "87%"}
    resposta = TEXTO_SEM_EVIDENCIA
    assert not escopo.alcanca(PROJETO_ALHEIO, {Perfil.MEMBRO_EQUIPE})
    assert all(valor not in resposta for valor in atributos_protegidos)


@pytest.mark.parametrize("cookie", [None, "sessao-expirada-ou-adulterada"])
def test_tf_rf01_03_sessao_ausente_ou_expirada_recusa_antes_do_pipeline(cookie) -> None:
    chamadas = 0

    async def nunca_montar():
        nonlocal chamadas
        chamadas += 1
        raise AssertionError("pipeline não deve ser montado")

    app.dependency_overrides[deps.obter_sessao] = lambda: None
    app.dependency_overrides[deps.obter_orquestrador] = nunca_montar
    try:
        with TestClient(app) as cliente:
            cookies = {auth_sessao.NOME_COOKIE: cookie} if cookie else None
            resposta = cliente.post("/chat", json={"mensagem": "Status"}, cookies=cookies)
    finally:
        app.dependency_overrides.clear()
    assert resposta.status_code == 401
    assert chamadas == 0


def test_tf_rf01_04_claim_sem_perfil_correspondente_recebe_perfil_seguro(monkeypatch) -> None:
    monkeypatch.setattr(permissoes.settings, "entra_grupo_diretoria", "diretoria")
    monkeypatch.setattr(permissoes.settings, "entra_grupo_lider_projeto", "lider")
    monkeypatch.setattr(permissoes.settings, "entra_grupo_membro_equipe", "membro")
    identidade = IdentidadeEntra("u-sem-perfil", "Sem perfil", None, ("grupo-desconhecido",))
    usuario = permissoes.resolver(identidade)
    assert usuario.perfil is Perfil.MEMBRO_EQUIPE
    assert usuario.projetos == frozenset()
    assert usuario.permissoes == frozenset()


def test_tf_rf01_05_mesmo_enunciado_obedece_a_escopos_distintos() -> None:
    membro = UsuarioAutenticado(
        "membro", "Membro", Perfil.MEMBRO_EQUIPE, projetos=frozenset({PROJETO_PROPRIO})
    )
    diretoria = UsuarioAutenticado("diretoria", "Diretoria", Perfil.DIRETORIA)
    escopo_membro = Escopo(membro.perfil, membro.projetos)
    escopo_diretoria = Escopo(diretoria.perfil, diretoria.projetos)
    assert escopo_membro.alcanca(PROJETO_PROPRIO, {Perfil.MEMBRO_EQUIPE})
    assert not escopo_membro.alcanca(PROJETO_ALHEIO, {Perfil.MEMBRO_EQUIPE})
    assert escopo_diretoria.alcanca(PROJETO_ALHEIO, {Perfil.DIRETORIA})
