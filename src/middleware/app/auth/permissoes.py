"""Tradução de grupos do Entra ID em perfil e permissões.

Nenhuma lista de usuários vive no código. Quem concede acesso é o
administrador do tenant, adicionando a pessoa a um grupo de segurança; o
middleware apenas traduz. Isso mantém a gestão de acesso onde o Metrô já
a opera e evita que uma mudança de time vire um deploy.

O mapeamento em si é configuração (ids de grupo variam entre tenants de
desenvolvimento e produção), por isso vem de variáveis de ambiente e não
de constantes daqui.

Perfil e permissão são independentes — ver schemas/usuario.py. Um usuário
pode ter perfil `MEMBRO_EQUIPE` e ainda assim `VER_INTENCOES`, se for
quem cuida da governança do catálogo.
"""

from app.auth.entra import IdentidadeEntra
from app.config import settings
from app.schemas.usuario import Perfil, Permissao, UsuarioAutenticado

# Perfil aplicado a quem se autentica mas não pertence a nenhum grupo
# mapeado. O mais restritivo de propósito: um grupo esquecido no
# provisionamento deve resultar em menos acesso, nunca em mais.
PERFIL_PADRAO = Perfil.MEMBRO_EQUIPE


def _grupos_por_perfil() -> list[tuple[Perfil, str]]:
    """Grupos de perfil, do mais amplo para o mais restrito."""
    return [
        (Perfil.DIRETORIA, settings.entra_grupo_diretoria),
        (Perfil.LIDER_PROJETO, settings.entra_grupo_lider_projeto),
        (Perfil.MEMBRO_EQUIPE, settings.entra_grupo_membro_equipe),
    ]


def _grupos_por_permissao() -> list[tuple[Permissao, str]]:
    return [
        (Permissao.VER_INTENCOES, settings.entra_grupo_ver_intencoes),
        (Permissao.GERIR_ROTINAS, settings.entra_grupo_gerir_rotinas),
    ]


def resolver(identidade: IdentidadeEntra) -> UsuarioAutenticado:
    """Monta o usuário autenticado a partir das claims do Entra ID.

    Quando a pessoa pertence a mais de um grupo de perfil, vale o mais
    amplo — a alternativa (recusar acesso por ambiguidade) transformaria
    uma configuração descuidada do tenant em indisponibilidade.
    """
    return UsuarioAutenticado(
        id=identidade.oid,
        nome=identidade.nome,
        perfil=perfil_de(identidade.grupos),
        permissoes=permissoes_de(identidade.grupos),
        email=identidade.email,
    )


def perfil_de(grupos: tuple[str, ...]) -> Perfil:
    """Traduz os grupos de segurança no perfil do usuário.

    Um grupo não configurado (string vazia) nunca casa, para que uma
    variável esquecida no .env não vire critério de acesso.
    """
    presentes = set(grupos)
    for perfil, grupo in _grupos_por_perfil():
        if grupo and grupo in presentes:
            return perfil
    return PERFIL_PADRAO


def permissoes_de(grupos: tuple[str, ...]) -> frozenset[Permissao]:
    """Traduz os grupos de segurança nas permissões concedidas."""
    presentes = set(grupos)
    return frozenset(
        permissao for permissao, grupo in _grupos_por_permissao() if grupo and grupo in presentes
    )
