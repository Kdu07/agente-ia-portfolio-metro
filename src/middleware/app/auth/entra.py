"""Fluxo Authorization Code + PKCE contra o Microsoft Entra ID.

Único módulo que fala com o provedor de identidade. Trocar o Entra ID
por outro IdP no futuro significa substituir apenas este arquivo — o
resto do middleware conhece `UsuarioAutenticado`, não OAuth.

Por que PKCE mesmo com o fluxo rodando no servidor: o `code_verifier`
protege contra interceptação do código de autorização no redirect, que
passa pelo navegador do usuário independentemente de onde a troca por
token acontece. É barato e fecha um vetor real.

TODO (onda 1): implementar com MSAL Python (ConfidentialClientApplication)
usando settings.entra_tenant_id, settings.entra_client_id,
settings.entra_client_secret e settings.entra_redirect_uri.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class DesafioAutorizacao:
    """O que precisa ser guardado entre o /login e o /callback."""

    url_autorizacao: str  # para onde redirecionar o navegador
    estado: str  # anti-CSRF; conferido no callback
    code_verifier: str  # PKCE; nunca sai do servidor


@dataclass(frozen=True)
class IdentidadeEntra:
    """Claims relevantes do token de identidade, já validadas.

    Deliberadamente cru: a tradução para `Perfil` e `Permissao` acontece
    em permissoes.py, para que a regra de negócio de acesso não fique
    espalhada dentro do cliente OAuth.
    """

    oid: str  # identificador estável do usuário no tenant
    nome: str
    email: str | None
    grupos: tuple[str, ...]  # ids dos grupos de segurança do Entra ID


def iniciar_autorizacao() -> DesafioAutorizacao:
    """Monta a URL de autorização e o par estado/verifier."""
    raise NotImplementedError("Integração com o Entra ID pendente (onda 1)")


async def trocar_codigo(codigo: str, code_verifier: str) -> IdentidadeEntra:
    """Troca o código de autorização pelo token e devolve as claims.

    Valida assinatura, emissor, audiência e expiração antes de devolver.
    Um token que não passe em qualquer dessas verificações deve levantar
    exceção, nunca devolver identidade parcial.
    """
    raise NotImplementedError("Integração com o Entra ID pendente (onda 1)")
