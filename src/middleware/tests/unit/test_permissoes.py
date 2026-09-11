"""Testes da tradução de grupos do Entra ID em perfil e permissões."""

import pytest

from app.auth import permissoes
from app.auth.entra import IdentidadeEntra
from app.config import settings
from app.schemas.usuario import Perfil, Permissao


@pytest.fixture(autouse=True)
def grupos_configurados(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "entra_grupo_diretoria", "g-diretoria")
    monkeypatch.setattr(settings, "entra_grupo_lider_projeto", "g-lider")
    monkeypatch.setattr(settings, "entra_grupo_membro_equipe", "g-membro")
    monkeypatch.setattr(settings, "entra_grupo_ver_intencoes", "g-intencoes")
    monkeypatch.setattr(settings, "entra_grupo_gerir_rotinas", "g-rotinas")


@pytest.mark.parametrize(
    ("grupos", "perfil"),
    [
        (("g-diretoria",), Perfil.DIRETORIA),
        (("g-lider",), Perfil.LIDER_PROJETO),
        (("g-membro",), Perfil.MEMBRO_EQUIPE),
        # Mais de um grupo de perfil: vale o mais amplo.
        (("g-membro", "g-lider"), Perfil.LIDER_PROJETO),
        (("g-lider", "g-diretoria", "g-membro"), Perfil.DIRETORIA),
        # Nenhum grupo mapeado: o mais restrito.
        ((), Perfil.MEMBRO_EQUIPE),
        (("grupo-de-outro-sistema",), Perfil.MEMBRO_EQUIPE),
    ],
)
def test_perfil_de(grupos: tuple[str, ...], perfil: Perfil) -> None:
    assert permissoes.perfil_de(grupos) is perfil


def test_permissoes_sao_independentes_do_perfil() -> None:
    assert permissoes.permissoes_de(("g-membro", "g-intencoes")) == {Permissao.VER_INTENCOES}
    assert permissoes.permissoes_de(("g-diretoria",)) == frozenset()
    assert permissoes.permissoes_de(("g-intencoes", "g-rotinas")) == {
        Permissao.VER_INTENCOES,
        Permissao.GERIR_ROTINAS,
    }


def test_grupo_nao_configurado_nunca_casa(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "entra_grupo_diretoria", "")
    monkeypatch.setattr(settings, "entra_grupo_gerir_rotinas", "")
    assert permissoes.perfil_de(("",)) is Perfil.MEMBRO_EQUIPE
    assert permissoes.permissoes_de(("",)) == frozenset()


def test_resolver_monta_o_usuario_a_partir_da_identidade() -> None:
    usuario = permissoes.resolver(
        IdentidadeEntra(
            oid="oid-1",
            nome="Mirela Bianchi",
            email="mirela@metro.example",
            grupos=("g-membro", "g-intencoes"),
        )
    )
    assert usuario.id == "oid-1"
    assert usuario.nome == "Mirela Bianchi"
    assert usuario.email == "mirela@metro.example"
    assert usuario.perfil is Perfil.MEMBRO_EQUIPE
    assert usuario.pode(Permissao.VER_INTENCOES)
    assert not usuario.pode(Permissao.GERIR_ROTINAS)
