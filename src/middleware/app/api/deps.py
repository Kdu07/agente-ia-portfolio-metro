"""Dependências compartilhadas pelas rotas (FastAPI Depends).

Responsabilidade central: autenticar o usuário e resolver seu perfil e
permissões ANTES de qualquer processamento. O controle de acesso por
perfil (requisito do projeto) é aplicado aqui, na porta de entrada.

TODO (sprint técnica): integrar com o provedor de identidade definido
(ex.: Microsoft Entra ID / OAuth2 do tenant do Metrô).
"""

from dataclasses import dataclass


@dataclass
class UsuarioAutenticado:
    """Identidade e permissões do usuário resolvidas na autenticação."""

    id: str
    nome: str
    perfil: str  # ex.: "gerente_portfolio", "lider_projeto", "consulta"


async def obter_usuario_atual() -> UsuarioAutenticado:
    """Valida o token da requisição e devolve o usuário autenticado.

    Levanta HTTP 401 se o token for inválido/ausente e HTTP 403 se o
    perfil não tiver acesso ao agente.
    """
    raise NotImplementedError("Integração com o provedor de identidade pendente")
