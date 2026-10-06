"""Dependências compartilhadas pelas rotas (FastAPI Depends).

Quatro responsabilidades:

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
4. Entregar o produtor de eventos criado no lifespan (app/main.py), que
   as rotas usam para publicar no RabbitMQ; os testes o trocam por um
   dublê pelo mesmo `dependency_overrides`.
"""

from collections.abc import Callable
from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.auth import sessao as auth_sessao
from app.executor.base import Executor
from app.executor.fabrica import montar_executor
from app.mensageria.produtor import ProdutorEventos
from app.persistence.repository import (
    AudioRepository,
    ConversaRepository,
    ConversaRepositoryTransacional,
    ExecucaoRepository,
    InteracaoRepository,
    InteracaoRepositoryTransacional,
    RotinaRepository,
    UsuarioRepository,
)
from app.persistence.repository_portfolio import (
    IndicadorRepository,
    MarcoRepository,
    ProjetoRepository,
    RiscoRepository,
    UsuarioProjetoRepository,
)
from app.persistence.sessao import fabrica_de_sessoes, obter_sessao
from app.pipeline.orquestrador import Orquestrador
from app.schemas.usuario import Permissao, UsuarioAutenticado
from app.servicos.processamento_audio import ProcessadorAudio

__all__ = [
    "AudioRepository",
    "FabricaSessoes",
    "Produtor",
    "SessaoBanco",
    "UsuarioAtual",
    "UsuarioAutenticado",
    "exige_permissao",
    "obter_audios",
    "obter_conversas",
    "obter_execucoes",
    "obter_executor",
    "obter_fabrica_sessoes",
    "obter_indicadores",
    "obter_interacoes",
    "obter_marcos",
    "obter_orquestrador",
    "obter_processador_audio",
    "obter_produtor",
    "obter_projetos",
    "obter_riscos",
    "obter_rotinas",
    "obter_usuario_atual",
    "obter_usuario_projeto",
    "obter_usuarios",
]

SessaoBanco = Annotated[AsyncSession, Depends(obter_sessao)]


def obter_fabrica_sessoes() -> async_sessionmaker[AsyncSession]:
    """Fábrica para operações que precisam delimitar a própria transação."""
    return fabrica_de_sessoes()


FabricaSessoes = Annotated[async_sessionmaker[AsyncSession], Depends(obter_fabrica_sessoes)]


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
    # A autenticação é a primeira consulta do /chat. Confirmar aqui devolve
    # a conexão ao pool antes de Content Safety, classificador e executor.
    # A AsyncSession continua utilizável caso outra dependência realmente
    # precise dela depois.
    await banco.commit()
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


def obter_executor(banco: SessaoBanco, usuario: UsuarioAtual) -> Executor:
    """Entrega à rota o executor montado pela fábrica compartilhada.

    O executor próprio é montado por requisição porque recupera no
    escopo de quem pergunta, e a porta não recebe o usuário: o `Escopo`
    nasce aqui, da identidade resolvida pela autenticação, e não é
    deduzido em nenhum lugar adiante. O `usuario` é o mesmo da rota — o
    FastAPI resolve a dependência uma vez por requisição.

    As decisões por `settings.executor` e pelo executor sintético ficam em
    `executor/fabrica.py`, também usada por áudio e worker. Assim os canais
    não criam caminhos divergentes.
    """
    return montar_executor(banco, usuario)


def obter_interacoes(banco: SessaoBanco) -> InteracaoRepository:
    """Repositório do registro de interações."""
    return InteracaoRepository(banco)


def obter_audios(banco: SessaoBanco) -> AudioRepository:
    """Repositorio das submissoes de audio do usuario."""
    return AudioRepository(banco)


def obter_processador_audio() -> ProcessadorAudio:
    """Processador que abre transacoes proprias depois da resposta 202."""
    return ProcessadorAudio()


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
    executor: Annotated[Executor, Depends(obter_executor)],
    fabrica: FabricaSessoes,
) -> Orquestrador:
    """Monta o orquestrador com seus colaboradores.

    Cada operação de persistência recebe uma transação curta. Assim a conexão
    usada para resolver a conversa ou ler o histórico volta ao pool antes das
    esperas externas do pipeline. A interação final continua sendo confirmada
    antes de a resposta HTTP ser entregue.
    """
    return Orquestrador(
        executor=executor,
        interacoes=InteracaoRepositoryTransacional(fabrica),
        conversas=ConversaRepositoryTransacional(fabrica),
    )


def obter_produtor(request: Request) -> ProdutorEventos:
    """Devolve o produtor único do processo, criado no lifespan.

    Um produtor por requisição abriria uma conexão AMQP a cada chamada;
    o do lifespan mantém uma só, com reconexão.
    """
    return request.app.state.produtor_eventos


Produtor = Annotated[ProdutorEventos, Depends(obter_produtor)]
