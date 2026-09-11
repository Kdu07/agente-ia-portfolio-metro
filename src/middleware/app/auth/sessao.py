"""Sessão do usuário em cookie httpOnly.

O cookie carrega um identificador de sessão assinado, não o access_token
do Entra ID nem as permissões em claro. Duas razões:

1. um cookie legível permitiria ao usuário editar o próprio perfil e
   conceder-se `VER_INTENCOES` — o servidor precisa ser a fonte da
   verdade sobre quem pode o quê;
2. o token do Entra ID nunca deve trafegar para o navegador, que é
   exatamente a propriedade que justifica o FastAPI como BFF.

Atributos obrigatórios do cookie (aplicados em api/routes/auth.py):
    httpOnly   — JavaScript não lê, o que neutraliza roubo por XSS
    Secure     — só trafega em HTTPS
    SameSite   — Strict; o app não é embutido em terceiros
    Max-Age    — expiração explícita, igual à da sessão no servidor

O estado da sessão fica no PostgreSQL (tabela `sessao_usuario`), o que dá
revogação imediata — um JWT autocontido continuaria valendo até expirar.
A assinatura do cookie com `settings.session_secret` é a segunda camada:
trocar o segredo invalida todas as sessões de uma vez, sem tocar o banco.

Este módulo também assina o cookie curto do fluxo de login (estado,
verifier e nonce entre /login e /callback), pela mesma razão: o servidor
precisa reconhecer o que ele mesmo emitiu.
"""

import hashlib
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from itsdangerous import BadData, URLSafeTimedSerializer
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.entra import ConfiguracaoAusente, FluxoPendente
from app.config import settings
from app.persistence.tabelas import SessaoUsuarioTabela, UsuarioTabela
from app.schemas.usuario import Perfil, Permissao, UsuarioAutenticado

NOME_COOKIE = "sessao"
NOME_COOKIE_FLUXO = "fluxo_login"

# Tempo para a pessoa concluir o login no Entra. Passado isso, o
# callback recusa e ela recomeça — um fluxo pendente não deve valer
# indefinidamente.
DURACAO_FLUXO_SEGUNDOS = 600

# Salts distintos impedem que um cookie de fluxo seja aceito como de
# sessão e vice-versa, embora os dois usem o mesmo segredo.
_SALT_SESSAO = "sessao"
_SALT_FLUXO = "fluxo-login"


@dataclass(frozen=True)
class Sessao:
    """Estado de sessão guardado no servidor."""

    id: str
    usuario: UsuarioAutenticado
    criada_em: datetime
    expira_em: datetime


def _serializador(salt: str) -> URLSafeTimedSerializer:
    if not settings.session_secret:
        raise ConfiguracaoAusente("Variável ausente: session_secret")
    return URLSafeTimedSerializer(settings.session_secret, salt=salt)


def _id_de(token: str) -> str:
    return hashlib.sha256(token.encode("ascii")).hexdigest()


# --- Fluxo de login ------------------------------------------------------


def assinar_fluxo(fluxo: FluxoPendente) -> str:
    """Valor do cookie que leva o fluxo pendente até o callback."""
    return _serializador(_SALT_FLUXO).dumps(
        {"estado": fluxo.estado, "verifier": fluxo.code_verifier, "nonce": fluxo.nonce}
    )


def ler_fluxo(valor_cookie: str | None) -> FluxoPendente | None:
    """Recupera o fluxo pendente, ou None se ausente, adulterado ou vencido."""
    if not valor_cookie:
        return None
    try:
        dados = _serializador(_SALT_FLUXO).loads(valor_cookie, max_age=DURACAO_FLUXO_SEGUNDOS)
        return FluxoPendente(
            estado=dados["estado"], code_verifier=dados["verifier"], nonce=dados["nonce"]
        )
    except (BadData, KeyError, TypeError):
        return None


# --- Sessão --------------------------------------------------------------


async def criar(banco: AsyncSession, usuario: UsuarioAutenticado) -> tuple[Sessao, str]:
    """Abre uma sessão para o usuário recém-autenticado.

    Devolve a sessão e o valor do cookie. O usuário já precisa existir em
    `usuario` — quem o garante é o callback, antes de chamar aqui.

    Aproveita o login para apagar as sessões vencidas da mesma pessoa:
    sem isso a tabela só cresceria, e um job de limpeza à parte seria
    mais uma peça no `worker` para uma tabela deste tamanho.
    """
    agora = datetime.now(UTC)
    token = secrets.token_urlsafe(32)
    sessao = Sessao(
        id=_id_de(token),
        usuario=usuario,
        criada_em=agora,
        expira_em=agora + timedelta(seconds=settings.session_max_age_seconds),
    )
    valor_cookie = _serializador(_SALT_SESSAO).dumps(token)

    await banco.execute(
        delete(SessaoUsuarioTabela).where(
            SessaoUsuarioTabela.usuario_id == usuario.id,
            SessaoUsuarioTabela.expira_em <= agora,
        )
    )
    banco.add(
        SessaoUsuarioTabela(
            id=sessao.id,
            usuario_id=usuario.id,
            perfil=usuario.perfil.value,
            permissoes=sorted(p.value for p in usuario.permissoes),
            criada_em=sessao.criada_em,
            expira_em=sessao.expira_em,
        )
    )
    await banco.flush()
    return sessao, valor_cookie


def _token_de(valor_cookie: str) -> str | None:
    # Sem segredo nenhuma sessão pode ter sido emitida. Devolver None faz
    # a requisição cair no 401, o frontend ir ao /auth/login e o 503 de
    # lá dizer o que falta — em vez de um 500 em cada rota.
    if not settings.session_secret:
        return None
    try:
        return _serializador(_SALT_SESSAO).loads(
            valor_cookie, max_age=settings.session_max_age_seconds
        )
    except BadData:
        return None


async def resolver(banco: AsyncSession, valor_cookie: str) -> Sessao | None:
    """Valida o cookie e devolve a sessão, ou None se inválida/expirada.

    Devolve None em vez de levantar: distinguir "cookie adulterado" de
    "sessão expirada" na resposta HTTP daria a um atacante um oráculo
    para testar assinaturas. Ambos os casos viram 401.
    """
    token = _token_de(valor_cookie)
    if token is None:
        return None

    linha = (
        await banco.execute(
            select(SessaoUsuarioTabela, UsuarioTabela)
            .join(UsuarioTabela, UsuarioTabela.id == SessaoUsuarioTabela.usuario_id)
            .where(
                SessaoUsuarioTabela.id == _id_de(token),
                SessaoUsuarioTabela.expira_em > datetime.now(UTC),
            )
        )
    ).first()
    if linha is None:
        return None

    registro, usuario = linha
    return Sessao(
        id=registro.id,
        usuario=UsuarioAutenticado(
            id=usuario.id,
            nome=usuario.nome,
            email=usuario.email,
            perfil=Perfil(registro.perfil),
            permissoes=frozenset(Permissao(p) for p in registro.permissoes),
        ),
        criada_em=registro.criada_em,
        expira_em=registro.expira_em,
    )


async def encerrar(banco: AsyncSession, valor_cookie: str) -> None:
    """Invalida no servidor a sessão do cookie (logout). Idempotente."""
    token = _token_de(valor_cookie)
    if token is None:
        return
    await banco.execute(delete(SessaoUsuarioTabela).where(SessaoUsuarioTabela.id == _id_de(token)))
