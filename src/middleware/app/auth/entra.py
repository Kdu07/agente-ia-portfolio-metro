"""Fluxo Authorization Code + PKCE contra o Microsoft Entra ID.

Único módulo que fala com o provedor de identidade. Trocar o Entra ID
por outro IdP no futuro significa substituir apenas este arquivo — o
resto do middleware conhece `UsuarioAutenticado`, não OAuth.

Por que PKCE mesmo com o fluxo rodando no servidor: o `code_verifier`
protege contra interceptação do código de autorização no redirect, que
passa pelo navegador do usuário independentemente de onde a troca por
token acontece. É barato e fecha um vetor real.

Por que httpx + PyJWT, e não MSAL: o MSAL é síncrono (usa `requests`),
faz descoberta de rede já no construtor e não confere a assinatura do
id_token — confia no TLS do endpoint de token. Aqui o fluxo cabe em duas
chamadas HTTP, a troca é assíncrona como o resto da API e a validação do
token é explícita e testável com uma chave gerada no próprio teste.

Nenhuma configuração é lida na importação: tenant, cliente e segredo vêm
de `settings` a cada chamada, para que os testes possam trocá-los e para
que um ambiente sem Entra configurado suba a API normalmente e só
recuse o login (503), em vez de não subir.
"""

import asyncio
import base64
import hashlib
import logging
import secrets
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

import httpx
import jwt

from app.config import settings

logger = logging.getLogger(__name__)

AUTORIDADE = "https://login.microsoftonline.com"

# Só os escopos OIDC: o middleware precisa saber QUEM é o usuário, não
# agir em nome dele em outra API. Pedir mais (User.Read, offline_access)
# ampliaria o consentimento e traria um refresh token que nada aqui usa.
ESCOPOS = "openid profile email"

# Folga para relógios dessincronizados entre o servidor e o Entra ID.
# Sem ela, um `iat` alguns segundos no futuro recusaria um token legítimo.
FOLGA_RELOGIO_SEGUNDOS = 60

TIMEOUT_SEGUNDOS = 10.0


class ConfiguracaoAusente(RuntimeError):
    """O ambiente não tem o que o login precisa (tenant, cliente, segredo)."""


class FalhaAutenticacao(Exception):
    """O Entra ID recusou a troca ou devolveu um token que não confere.

    A mensagem é para o log, nunca para o usuário: detalhar ao navegador
    por que um token foi recusado ajudaria quem tenta forjá-lo.
    """


@dataclass(frozen=True)
class FluxoPendente:
    """O que precisa sobreviver entre o /login e o /callback.

    Viaja num cookie assinado e httpOnly (ver auth/sessao.py): o
    JavaScript não o lê, e o servidor recusa qualquer versão adulterada.
    """

    estado: str  # anti-CSRF; conferido no callback
    code_verifier: str  # PKCE; o Entra só aceita o código com ele
    nonce: str  # amarra o id_token a este fluxo; conferido no token


@dataclass(frozen=True)
class DesafioAutorizacao:
    """Resultado do início do fluxo: para onde ir e o que guardar."""

    url_autorizacao: str  # para onde redirecionar o navegador
    fluxo: FluxoPendente


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


def _exigir_configuracao() -> None:
    faltando = [
        nome
        for nome in ("entra_tenant_id", "entra_client_id", "entra_client_secret")
        if not getattr(settings, nome)
    ]
    if faltando:
        raise ConfiguracaoAusente(f"Variáveis ausentes: {', '.join(faltando)}")


def _url_tenant() -> str:
    return f"{AUTORIDADE}/{settings.entra_tenant_id}"


def _emissor() -> str:
    """Emissor esperado do id_token v2.0.

    O Entra escreve o GUID do tenant no `iss`. Por isso ENTRA_TENANT_ID
    precisa ser o GUID, e não o domínio (contoso.onmicrosoft.com): com o
    domínio a URL de autorização funciona, mas todo token seria recusado.
    """
    return f"{_url_tenant()}/v2.0"


def _desafio_pkce(verifier: str) -> str:
    """code_challenge S256: base64url(sha256(verifier)), sem padding."""
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def iniciar_autorizacao() -> DesafioAutorizacao:
    """Monta a URL de autorização e o trio estado/verifier/nonce."""
    _exigir_configuracao()
    fluxo = FluxoPendente(
        estado=secrets.token_urlsafe(32),
        # 64 bytes viram 86 caracteres, dentro dos 43-128 da RFC 7636.
        code_verifier=secrets.token_urlsafe(64),
        nonce=secrets.token_urlsafe(32),
    )
    parametros = {
        "client_id": settings.entra_client_id,
        "response_type": "code",
        "redirect_uri": settings.entra_redirect_uri,
        "response_mode": "query",
        "scope": ESCOPOS,
        "state": fluxo.estado,
        "nonce": fluxo.nonce,
        "code_challenge": _desafio_pkce(fluxo.code_verifier),
        "code_challenge_method": "S256",
    }
    url = f"{_url_tenant()}/oauth2/v2.0/authorize?{urlencode(parametros)}"
    return DesafioAutorizacao(url_autorizacao=url, fluxo=fluxo)


async def trocar_codigo(
    codigo: str,
    fluxo: FluxoPendente,
    *,
    http: httpx.AsyncClient | None = None,
) -> IdentidadeEntra:
    """Troca o código de autorização pelo token e devolve as claims.

    Valida assinatura, emissor, audiência, expiração e nonce antes de
    devolver. Um token que não passe em qualquer dessas verificações
    levanta `FalhaAutenticacao`, nunca devolve identidade parcial.

    `http` existe para os testes injetarem um transporte dublado; em
    produção cada troca abre o próprio cliente, porque o login é raro
    demais para justificar um pool vivo pelo processo inteiro.
    """
    _exigir_configuracao()
    dados = {
        "client_id": settings.entra_client_id,
        "client_secret": settings.entra_client_secret,
        "grant_type": "authorization_code",
        "code": codigo,
        "redirect_uri": settings.entra_redirect_uri,
        "code_verifier": fluxo.code_verifier,
        "scope": ESCOPOS,
    }
    url = f"{_url_tenant()}/oauth2/v2.0/token"

    try:
        if http is None:
            async with httpx.AsyncClient(timeout=TIMEOUT_SEGUNDOS) as cliente:
                resposta = await cliente.post(url, data=dados)
        else:
            resposta = await http.post(url, data=dados)
    except httpx.HTTPError as erro:
        raise FalhaAutenticacao(f"Endpoint de token inacessível: {erro!r}") from erro

    corpo = _json_ou_vazio(resposta)
    if resposta.status_code != 200 or "id_token" not in corpo:
        # `error` e `error_codes` identificam a causa (AADSTS...) sem
        # carregar dado pessoal; `error_description` às vezes carrega o
        # UPN do usuário e fica de fora do log.
        raise FalhaAutenticacao(
            f"Troca recusada ({resposta.status_code}): "
            f"{corpo.get('error')} {corpo.get('error_codes')}"
        )

    claims = await validar_id_token(corpo["id_token"], fluxo.nonce)
    return _identidade(claims)


def _json_ou_vazio(resposta: httpx.Response) -> dict[str, Any]:
    try:
        corpo = resposta.json()
    except ValueError:
        return {}
    return corpo if isinstance(corpo, dict) else {}


async def validar_id_token(token: str, nonce: str) -> dict[str, Any]:
    """Confere o id_token e devolve as claims.

    A assinatura é conferida mesmo com o token chegando direto do
    endpoint de token por TLS — a especificação OIDC permite dispensá-la
    nesse caso, mas conferir custa uma chave em cache e tira do caminho a
    pergunta "e se o TLS estiver sendo inspecionado".
    """
    try:
        chave = await asyncio.to_thread(_chave_de_assinatura, token)
        claims = jwt.decode(
            token,
            chave,
            algorithms=["RS256"],
            audience=settings.entra_client_id,
            issuer=_emissor(),
            leeway=FOLGA_RELOGIO_SEGUNDOS,
            options={"require": ["exp", "iat", "iss", "aud", "oid", "nonce"]},
        )
    except jwt.PyJWTError as erro:
        raise FalhaAutenticacao(f"id_token recusado: {erro!r}") from erro

    if not secrets.compare_digest(str(claims["nonce"]), nonce):
        raise FalhaAutenticacao("id_token recusado: nonce não confere com o fluxo")
    return claims


# Um cliente por processo: o PyJWKClient guarda as chaves públicas em
# cache e só volta ao Entra quando aparece um `kid` desconhecido — que é
# como a rotação de chaves do tenant chega até aqui.
_jwks: jwt.PyJWKClient | None = None


def _chave_de_assinatura(token: str) -> Any:
    """Chave pública do tenant que assinou o token (bloqueante)."""
    global _jwks
    uri = f"{_url_tenant()}/discovery/v2.0/keys"
    if _jwks is None or _jwks.uri != uri:
        _jwks = jwt.PyJWKClient(uri, cache_keys=True, timeout=int(TIMEOUT_SEGUNDOS))
    return _jwks.get_signing_key_from_jwt(token).key


def _identidade(claims: dict[str, Any]) -> IdentidadeEntra:
    """Extrai do token o que o middleware usa."""
    grupos: tuple[str, ...] = tuple(claims.get("groups", ()))
    if "groups" in claims.get("_claim_names", {}):
        # Overage: acima de 200 grupos o Entra troca a lista por uma
        # referência ao Graph. Seguir a referência exigiria permissão de
        # leitura de grupos no tenant; em vez disso, o usuário entra com o
        # perfil mais restrito e o log aponta a correção — atribuir os
        # grupos ao aplicativo e emitir só "Groups assigned to the
        # application" no token.
        logger.warning(
            "Token do usuário %s veio com overage de grupos; aplicado o perfil padrão.",
            claims["oid"],
        )
        grupos = ()

    return IdentidadeEntra(
        oid=claims["oid"],
        nome=claims.get("name") or claims.get("preferred_username") or claims["oid"],
        # `email` só vem quando configurado como claim opcional; o
        # `preferred_username` (UPN) é o melhor substituto em conta
        # corporativa, mas não é garantidamente um endereço.
        email=claims.get("email") or claims.get("preferred_username"),
        grupos=grupos,
    )
