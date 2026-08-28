"""Rotas de autenticação — o FastAPI como BFF do Entra ID.

Três endpoints e nenhum token no navegador:

    GET  /auth/login     redireciona ao Entra ID
    GET  /auth/callback  troca o código, abre a sessão, seta o cookie
    POST /auth/logout    invalida a sessão no servidor
    GET  /auth/eu        quem é o usuário da sessão atual

`/auth/eu` existe porque o cookie é httpOnly: o React não consegue lê-lo
para descobrir quem está logado nem quais permissões tem. Sem esta rota
o app não saberia se deve exibir as abas de intenções e rotinas.

Nota: o que `/auth/eu` devolve é conveniência de interface, não controle
de acesso. Quem barra continua sendo `exige_permissao` em cada rota.
"""

from fastapi import APIRouter, Response, status
from pydantic import BaseModel

from app.api.deps import UsuarioAtual

router = APIRouter(prefix="/auth")


class UsuarioResposta(BaseModel):
    """Identidade da sessão atual, para o frontend montar a navegação."""

    id: str
    nome: str
    email: str | None
    perfil: str
    permissoes: list[str]


@router.get("/login")
async def login() -> Response:
    """Redireciona ao Entra ID iniciando o fluxo Authorization Code + PKCE.

    TODO (onda 1): chamar auth.entra.iniciar_autorizacao(), guardar
    `estado` e `code_verifier` em cookie temporário httpOnly e devolver
    RedirectResponse para a URL de autorização.
    """
    raise NotImplementedError("Fluxo de login a implementar na onda 1")


@router.get("/callback")
async def callback(code: str, state: str) -> Response:
    """Recebe o retorno do Entra ID e abre a sessão.

    TODO (onda 1): conferir `state` contra o cookie temporário (anti-CSRF),
    chamar auth.entra.trocar_codigo(), traduzir via auth.permissoes.resolver(),
    abrir a sessão e setar o cookie com httpOnly, Secure, SameSite=Strict.

    Um `state` que não confere deve resultar em 400 e nenhuma sessão: é o
    sinal de que o fluxo não começou neste navegador.
    """
    raise NotImplementedError("Callback a implementar na onda 1")


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(usuario: UsuarioAtual) -> Response:
    """Invalida a sessão no servidor e limpa o cookie.

    Invalidar no servidor, e não apenas apagar o cookie, é o que torna o
    logout efetivo: um cookie copiado antes continuaria valendo se a
    sessão só existisse no cliente.
    """
    raise NotImplementedError("Logout a implementar na onda 1")


@router.get("/eu", response_model=UsuarioResposta)
async def eu(usuario: UsuarioAtual) -> UsuarioResposta:
    """Devolve a identidade da sessão atual."""
    return UsuarioResposta(
        id=usuario.id,
        nome=usuario.nome,
        email=usuario.email,
        perfil=usuario.perfil.value,
        permissoes=sorted(p.value for p in usuario.permissoes),
    )
