"""Sessão do usuário em cookie httpOnly.

O cookie carrega um identificador de sessão assinado, não o access_token
do Entra ID nem as permissões em claro. Duas razões:

1. um cookie legível permitiria ao usuário editar o próprio perfil e
   conceder-se `VER_INTENCOES` — o servidor precisa ser a fonte da
   verdade sobre quem pode o quê;
2. o token do Entra ID nunca deve trafegar para o navegador, que é
   exatamente a propriedade que justifica o FastAPI como BFF.

Atributos obrigatórios do cookie:
    httpOnly   — JavaScript não lê, o que neutraliza roubo por XSS
    Secure     — só trafega em HTTPS
    SameSite   — Strict; o app não é embutido em terceiros
    Max-Age    — expiração explícita, alinhada ao token do Entra ID

TODO (onda 1): implementar com itsdangerous ou JWT assinado por
settings.session_secret, com armazenamento do estado da sessão no
PostgreSQL (permite revogação imediata, que um JWT autocontido não dá).
"""

from dataclasses import dataclass
from datetime import datetime

from app.schemas.usuario import UsuarioAutenticado

NOME_COOKIE = "sessao"


@dataclass(frozen=True)
class Sessao:
    """Estado de sessão guardado no servidor."""

    id: str
    usuario: UsuarioAutenticado
    criada_em: datetime
    expira_em: datetime


async def criar(usuario: UsuarioAutenticado) -> Sessao:
    """Abre uma sessão para o usuário recém-autenticado."""
    raise NotImplementedError("Sessão a implementar na onda 1")


async def resolver(valor_cookie: str) -> Sessao | None:
    """Valida o cookie e devolve a sessão, ou None se inválida/expirada.

    Devolve None em vez de levantar: distinguir "cookie adulterado" de
    "sessão expirada" na resposta HTTP daria a um atacante um oráculo
    para testar assinaturas. Ambos os casos viram 401.
    """
    raise NotImplementedError("Sessão a implementar na onda 1")


async def encerrar(sessao_id: str) -> None:
    """Invalida a sessão no servidor (logout)."""
    raise NotImplementedError("Sessão a implementar na onda 1")
