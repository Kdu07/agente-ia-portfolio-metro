"""Rotas de autenticação — o FastAPI como BFF do Entra ID.

Quatro endpoints e nenhum token no navegador:

    GET  /auth/login     redireciona ao Entra ID
    GET  /auth/callback  troca o código, abre a sessão, seta o cookie
    POST /auth/logout    invalida a sessão no servidor
    GET  /auth/eu        quem é o usuário da sessão atual

`/auth/eu` existe porque o cookie é httpOnly: o React não consegue lê-lo
para descobrir quem está logado nem quais permissões tem. Sem esta rota
o app não saberia se deve exibir as abas de intenções e rotinas.

Nota: o que `/auth/eu` devolve é conveniência de interface, não controle
de acesso. Quem barra continua sendo `exige_permissao` em cada rota.

Os redirecionamentos para `/` e `/entrar` são relativos de propósito: o
navegador chega aqui pelo proxy `/api` (Vite em desenvolvimento, Nginx no
contêiner), e na origem dele essas são as rotas do React.
"""

import logging
import secrets
from typing import Annotated, Literal

from fastapi import APIRouter, Cookie, HTTPException, Response, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from app.api.deps import SessaoBanco, UsuarioAtual
from app.auth import entra, permissoes
from app.auth import sessao as auth_sessao
from app.config import settings
from app.persistence.repository import UsuarioRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth")

DESTINO_APOS_LOGIN = "/"
DESTINO_FALHA_LOGIN = "/entrar?erro=login"


class UsuarioResposta(BaseModel):
    """Identidade da sessão atual, para o frontend montar a navegação."""

    id: str
    nome: str
    email: str | None
    perfil: str
    permissoes: list[str]


def _gravar_cookie(
    resposta: Response,
    nome: str,
    valor: str,
    max_age: int,
    samesite: Literal["lax", "strict"],
) -> None:
    # `path="/"` explícito: o navegador vê /api/auth/..., e sem o path o
    # cookie ficaria restrito a /api/auth e não voltaria nas outras rotas.
    resposta.set_cookie(
        nome,
        valor,
        max_age=max_age,
        path="/",
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite=samesite,
    )


def _apagar_cookie(resposta: Response, nome: str) -> None:
    resposta.delete_cookie(nome, path="/", httponly=True, secure=settings.session_cookie_secure)


@router.get("/login")
async def login() -> Response:
    """Redireciona ao Entra ID iniciando o fluxo Authorization Code + PKCE.

    O cookie do fluxo é SameSite=Lax, e não Strict como o de sessão: a
    volta do Entra ao /callback é uma navegação vinda de outro site, e um
    cookie Strict não seria enviado nela — todo login falharia no `state`.
    """
    try:
        desafio = entra.iniciar_autorizacao()
        valor = auth_sessao.assinar_fluxo(desafio.fluxo)
    except entra.ConfiguracaoAusente as erro:
        logger.error("Login indisponível: %s", erro)
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "Autenticação não configurada"
        ) from erro

    resposta = RedirectResponse(desafio.url_autorizacao, status.HTTP_302_FOUND)
    _gravar_cookie(
        resposta,
        auth_sessao.NOME_COOKIE_FLUXO,
        valor,
        max_age=auth_sessao.DURACAO_FLUXO_SEGUNDOS,
        samesite="lax",
    )
    return resposta


@router.get("/callback")
async def callback(
    banco: SessaoBanco,
    state: str | None = None,
    code: str | None = None,
    error: str | None = None,
    fluxo_cookie: Annotated[str | None, Cookie(alias=auth_sessao.NOME_COOKIE_FLUXO)] = None,
) -> Response:
    """Recebe o retorno do Entra ID e abre a sessão.

    Um `state` que não confere resulta em 400 e nenhuma sessão: é o sinal
    de que o fluxo não começou neste navegador. Já uma recusa do Entra
    (usuário cancelou, não tem acesso ao app) ou um token inválido levam
    de volta à tela de entrada — são desfechos esperados, não ataques.
    """
    fluxo = auth_sessao.ler_fluxo(fluxo_cookie)
    if fluxo is None or state is None or not secrets.compare_digest(state, fluxo.estado):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Fluxo de login inválido")

    if error or code is None:
        logger.info("Entra ID devolveu o login sem código: %s", error)
        return _falha_login()

    try:
        identidade = await entra.trocar_codigo(code, fluxo)
    except entra.FalhaAutenticacao as erro:
        logger.warning("Login recusado: %s", erro)
        return _falha_login()

    usuario = permissoes.resolver(identidade)
    await UsuarioRepository(banco).garantir(
        usuario_id=usuario.id,
        nome=usuario.nome,
        perfil=usuario.perfil.value,
        email=usuario.email,
    )
    _, valor_cookie = await auth_sessao.criar(banco, usuario)
    # Commit antes de responder, e não no fim da dependência: o navegador
    # segue o redirect e pede /auth/eu imediatamente, e a sessão precisa
    # estar visível para essa segunda requisição.
    await banco.commit()

    resposta = RedirectResponse(DESTINO_APOS_LOGIN, status.HTTP_303_SEE_OTHER)
    _apagar_cookie(resposta, auth_sessao.NOME_COOKIE_FLUXO)
    _gravar_cookie(
        resposta,
        auth_sessao.NOME_COOKIE,
        valor_cookie,
        max_age=settings.session_max_age_seconds,
        samesite="strict",
    )
    return resposta


def _falha_login() -> Response:
    resposta = RedirectResponse(DESTINO_FALHA_LOGIN, status.HTTP_303_SEE_OTHER)
    _apagar_cookie(resposta, auth_sessao.NOME_COOKIE_FLUXO)
    return resposta


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    banco: SessaoBanco,
    sessao: Annotated[str | None, Cookie(alias=auth_sessao.NOME_COOKIE)] = None,
) -> Response:
    """Invalida a sessão no servidor e limpa o cookie.

    Invalidar no servidor, e não apenas apagar o cookie, é o que torna o
    logout efetivo: um cookie copiado antes continuaria valendo se a
    sessão só existisse no cliente.

    Idempotente: sem sessão válida, apenas limpa o cookie e devolve 204.
    Um 401 aqui mandaria o frontend ao login justamente ao sair.

    Encerra só a sessão do middleware. A sessão no Entra ID continua, e o
    próximo login no mesmo navegador passa sem pedir senha — o mesmo
    comportamento dos apps Microsoft 365 ao sair de um só deles.
    """
    if sessao:
        await auth_sessao.encerrar(banco, sessao)
    resposta = Response(status_code=status.HTTP_204_NO_CONTENT)
    _apagar_cookie(resposta, auth_sessao.NOME_COOKIE)
    return resposta


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
