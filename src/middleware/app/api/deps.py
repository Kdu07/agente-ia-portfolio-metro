"""Dependências compartilhadas pelas rotas (FastAPI Depends).

Três responsabilidades:

1. Resolver a sessão e devolver o usuário autenticado ANTES de qualquer
   processamento. É a porta única de entrada de identidade: nenhuma rota
   deve ler o cookie por conta própria.
2. Exigir permissões específicas (`VER_INTENCOES`, `GERIR_ROTINAS`) nas
   rotas restritas. O frontend esconde essas telas por conveniência, mas
   quem barra é aqui — uma rota escondida no React é decoração, não
   controle de acesso.
3. Montar o orquestrador com seus colaboradores, inclusive o executor
   escolhido por `settings.executor`. Concentrar a montagem aqui é o que
   permite aos testes trocarem o executor por um dublê via
   `app.dependency_overrides`, sem monkeypatch.
"""

from collections.abc import Callable
from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import sessao as auth_sessao
from app.config import settings
from app.copilot.client import CopilotClient
from app.executor.base import Executor
from app.persistence.repository import (
    ConversaRepository,
    ExecucaoRepository,
    InteracaoRepository,
    RotinaRepository,
    UsuarioRepository,
)
from app.persistence.repository_portfolio import (
    ProjetoRepository,
    RiscoRepository,
    MarcoRepository,
    IndicadorRepository,
    UsuarioProjetoRepository,
)
from app.persistence.sessao import obter_sessao
from app.pipeline.orquestrador import Orquestrador
from app.schemas.usuario import Permissao, UsuarioAutenticado

__all__ = [
    "SessaoBanco",
    "UsuarioAtual",
    "UsuarioAutenticado",
    "exige_permissao",
    "obter_conversas",
    "obter_execucoes",
    "obter_executor",
    "obter_interacoes",
    "obter_indicadores",
    "obter_marcos",
    "obter_orquestrador",
    "obter_projetos",
    "obter_riscos",
    "obter_rotinas",
    "obter_usuario_atual",
    "obter_usuario_projeto",
    "obter_usuarios",
]

SessaoBanco = Annotated[AsyncSession, Depends(obter_sessao)]


async def obter_usuario_atual(
    banco: SessaoBanco,
    sessao: Annotated[str | None, Cookie(alias=auth_sessao.NOME_COOKIE)] = None,
) -> UsuarioAutenticado:
    """Resolve a sessão do cookie e devolve o usuário autenticado.

    Cookie ausente, adulterado ou expirado resultam no MESMO 401. A
    distinção seria um oráculo útil a quem tenta forjar sessões.

    Atualiza a projeção da identidade no banco antes de devolvê-la. A
    linha em `usuario` nasce no callback do login; aqui o upsert mantém
    `visto_em` como o último uso, e não o último login — é o que o
    dashboard precisa para distinguir quem existe de quem usa.

    Uma falha aqui propaga. Se o banco não responde, a requisição não
    teria como gravar nada mesmo; devolver 200 sugerindo o contrário
    seria pior.
    """
    if sessao is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sessão ausente")

    resolvida = await auth_sessao.resolver(banco, sessao)
    if resolvida is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sessão inválida")

    usuario = resolvida.usuario
    await UsuarioRepository(banco).garantir(
        usuario_id=usuario.id,
        nome=usuario.nome,
        perfil=usuario.perfil.value,
        email=usuario.email,
    )
    return usuario


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


EXECUTORES = ("copilot", "proprio")


def obter_executor(banco: SessaoBanco, usuario: UsuarioAtual) -> Executor:
    """O executor escolhido por `settings.executor` — único ponto dessa leitura.

    O executor próprio é montado por requisição porque recupera no
    escopo de quem pergunta, e a porta não recebe o usuário: o `Escopo`
    nasce aqui, da identidade resolvida pela autenticação, e não é
    deduzido em nenhum lugar adiante. O `usuario` é o mesmo da rota — o
    FastAPI resolve a dependência uma vez por requisição.

    O import é local para que o caminho `copilot` não exija o extra `rag`.
    """
    escolhido = settings.executor.strip().lower()

    if escolhido == "copilot":
        return CopilotClient()

    if escolhido == "proprio":
        from app.rag.executor import montar_executor

        return montar_executor(banco, usuario)

    raise ValueError(f"executor inválido: {escolhido!r}. Esperado um de {EXECUTORES}")


def obter_interacoes(banco: SessaoBanco) -> InteracaoRepository:
    """Repositório do registro de interações."""
    return InteracaoRepository(banco)


def obter_conversas(banco: SessaoBanco) -> ConversaRepository:
    """Repositório de sessões de conversa."""
    return ConversaRepository(banco)


def obter_rotinas(banco: SessaoBanco) -> RotinaRepository:
    """Repositório de rotinas."""
    return RotinaRepository(banco)


def obter_execucoes(banco: SessaoBanco) -> ExecucaoRepository:
    """Repositório do histórico de disparos."""
    return ExecucaoRepository(banco)


def obter_usuarios(banco: SessaoBanco) -> UsuarioRepository:
    """Repositório da projeção de identidade."""
    return UsuarioRepository(banco)


def obter_projetos(banco: SessaoBanco) -> ProjetoRepository:
    return ProjetoRepository(banco)


def obter_riscos(banco: SessaoBanco) -> RiscoRepository:
    return RiscoRepository(banco)


def obter_marcos(banco: SessaoBanco) -> MarcoRepository:
    return MarcoRepository(banco)


def obter_indicadores(banco: SessaoBanco) -> IndicadorRepository:
    return IndicadorRepository(banco)


def obter_usuario_projeto(banco: SessaoBanco) -> UsuarioProjetoRepository:
    return UsuarioProjetoRepository(banco)


def obter_orquestrador(
    interacoes: Annotated[InteracaoRepository, Depends(obter_interacoes)],
    conversas: Annotated[ConversaRepository, Depends(obter_conversas)],
    executor: Annotated[Executor, Depends(obter_executor)],
) -> Orquestrador:
    """Monta o orquestrador com seus colaboradores.

    Os repositórios chegam por `Depends` e compartilham a sessão da
    requisição: a conversa criada no início do turno e a interação
    gravada no fim são a mesma transação, e um erro entre as duas não
    deixa conversa órfã.
    """
    return Orquestrador(
        executor=executor,
        interacoes=interacoes,
        conversas=conversas,
    )
