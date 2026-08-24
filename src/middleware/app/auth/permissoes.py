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
from app.schemas.usuario import Perfil, Permissao, UsuarioAutenticado

# Perfil aplicado a quem se autentica mas não pertence a nenhum grupo
# mapeado. O mais restritivo de propósito: um grupo esquecido no
# provisionamento deve resultar em menos acesso, nunca em mais.
PERFIL_PADRAO = Perfil.MEMBRO_EQUIPE


def resolver(identidade: IdentidadeEntra) -> UsuarioAutenticado:
    """Monta o usuário autenticado a partir das claims do Entra ID.

    Quando a pessoa pertence a mais de um grupo de perfil, vale o mais
    amplo — a alternativa (recusar acesso por ambiguidade) transformaria
    uma configuração descuidada do tenant em indisponibilidade.

    TODO (onda 1): ler os mapeamentos de settings.entra_grupo_* e cruzar
    com identidade.grupos.
    """
    raise NotImplementedError("Mapeamento de grupos a implementar na onda 1")


def perfil_de(grupos: tuple[str, ...]) -> Perfil:
    """Traduz os grupos de segurança no perfil do usuário."""
    raise NotImplementedError("Mapeamento de grupos a implementar na onda 1")


def permissoes_de(grupos: tuple[str, ...]) -> frozenset[Permissao]:
    """Traduz os grupos de segurança nas permissões concedidas."""
    raise NotImplementedError("Mapeamento de grupos a implementar na onda 1")
