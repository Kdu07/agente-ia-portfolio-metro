"""Dependências compartilhadas pelas rotas (FastAPI Depends).

Três responsabilidades:

1. Resolver a sessão e devolver o usuário autenticado ANTES de qualquer
   processamento. É a porta única de entrada de identidade: nenhuma rota
   deve ler o cookie por conta própria.
2. Exigir permissões específicas (`VER_INTENCOES`, `GERIR_ROTINAS`) nas
   rotas restritas. O frontend esconde essas telas por conveniência, mas
   quem barra é aqui — uma rota escondida no React é decoração, não
   controle de acesso.
3. Montar o orquestrador com seus colaboradores. Concentrar a montagem
   aqui é o que permite aos testes trocarem o Copilot por um dublê via
   `app.dependency_overrides`, sem monkeypatch.
"""

from collections.abc import Callable
from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, status

from app.auth import sessao as auth_sessao
from app.copilot.client import CopilotClient
from app.persistence.repository import (
    ConversaRepository,
    ExecucaoRepository,
    InteracaoRepository,
    RotinaRepository,
)
from app.pipeline.orquestrador import Orquestrador
from app.schemas.usuario import Permissao, UsuarioAutenticado

__all__ = [
    "UsuarioAtual",
    "UsuarioAutenticado",
    "exige_permissao",
    "obter_conversas",
    "obter_copilot",
    "obter_execucoes",
    "obter_interacoes",
    "obter_orquestrador",
    "obter_rotinas",
    "obter_usuario_atual",
]


async def obter_usuario_atual(
    sessao: Annotated[str | None, Cookie(alias=auth_sessao.NOME_COOKIE)] = None,
) -> UsuarioAutenticado:
    """Resolve a sessão do cookie e devolve o usuário autenticado.

    Cookie ausente, adulterado ou expirado resultam no MESMO 401. A
    distinção seria um oráculo útil a quem tenta forjar sessões.
    """
    if sessao is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sessão ausente")

    resolvida = await auth_sessao.resolver(sessao)
    if resolvida is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sessão inválida")

    return resolvida.usuario


UsuarioAtual = Annotated[UsuarioAutenticado, Depends(obter_usuario_atual)]


def exige_permissao(permissao: Permissao) -> Callable[..., UsuarioAutenticado]:
    """Fábrica de dependência que exige uma permissão específica.

    Uso:
        @router.get("/", dependencies=[Depends(exige_permissao(Permissao.VER_INTENCOES))])

    Devolve 403, e não 404, quando o usuário está autenticado mas não tem
    a permissão: esconder a existência da rota não protege nada aqui — o
    frontend é servido ao mesmo público e as rotas são conhecidas.
    """

    def verificar(usuario: UsuarioAtual) -> UsuarioAutenticado:
        if not usuario.pode(permissao):
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                f"Acesso restrito: requer {permissao.value}",
            )
        return usuario

    return verificar


def obter_copilot() -> CopilotClient:
    """Cliente do executor. Ponto de troca nos testes de integração."""
    return CopilotClient()


def obter_interacoes() -> InteracaoRepository:
    """Repositório do registro de interações."""
    return InteracaoRepository()


def obter_conversas() -> ConversaRepository:
    """Repositório de sessões de conversa."""
    return ConversaRepository()


def obter_rotinas() -> RotinaRepository:
    """Repositório de rotinas."""
    return RotinaRepository()


def obter_execucoes() -> ExecucaoRepository:
    """Repositório do histórico de disparos."""
    return ExecucaoRepository()


def obter_orquestrador() -> Orquestrador:
    """Monta o orquestrador com seus colaboradores.

    TODO (onda 1): quando os repositórios tiverem implementação com pool
    de conexões, receber os providers acima via Depends em vez de
    instanciá-los por requisição.
    """
    return Orquestrador(
        copilot=obter_copilot(),
        interacoes=obter_interacoes(),
        conversas=obter_conversas(),
    )
