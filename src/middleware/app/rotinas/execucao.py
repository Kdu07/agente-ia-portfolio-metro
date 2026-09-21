"""Execução de uma rotina.

É aqui que a decisão mais importante do pacote se materializa: a rotina
entra pelo **mesmo orquestrador** que uma mensagem digitada, com
`canal=Canal.ROTINA`. Este módulo não importa `copilot/client.py`, e não
deve passar a importar.

A direção da dependência é a garantia:

    rotinas/execucao.py  ->  pipeline/orquestrador.py  ->  copilot/client.py

Se um dia aparecer uma seta direta de `rotinas/` para `copilot/`, as
guardas deixaram de ser obrigatórias e qualquer rotina cadastrada vira um
canal sem proteção — rodando periodicamente, sem ninguém olhando.

Identidade: a rotina executa como o dono, e o usuário é reconstruído no
momento do disparo, nunca guardado no cadastro. Uma permissão revogada
ontem precisa valer no disparo de hoje.
"""

import uuid
from dataclasses import replace
from datetime import UTC, datetime

from app.auth import entra, permissoes
from app.executor.fabrica import montar_executor
from app.persistence.models import Canal, ExecucaoRotina, Rotina, StatusExecucao
from app.persistence.repository import (
    ConversaRepository,
    ExecucaoRepository,
    InteracaoRepository,
    RotinaRepository,
    UsuarioRepository,
)
from app.persistence.repository_portfolio import UsuarioProjetoRepository
from app.persistence.sessao import fabrica_de_sessoes
from app.pipeline.desfechos import Desfecho
from app.pipeline.orquestrador import Orquestrador
from app.schemas.chat import ChatRequest, ChatResponse
from app.schemas.usuario import Permissao, UsuarioAutenticado


class RotinaNaoEncontrada(LookupError):
    """A rotina pedida para execução manual não existe."""


class ExecucaoNaoAutorizada(PermissionError):
    """O solicitante tentou executar a rotina de outra pessoa."""


class PermissaoRotinaRevogada(PermissionError):
    """O dono perdeu a permissão de gerenciar e executar rotinas."""


async def executar(rotina: Rotina) -> ChatResponse:
    """Dispara uma rotina através do pipeline completo.

    Passos previstos (onda 5):

    1. registrar o início em `ExecucaoRepository.registrar_inicio`, antes
       de qualquer chamada externa, para que uma rotina travada seja visível;
    2. reconstruir o `UsuarioAutenticado` do dono a partir do Entra ID —
       se o dono foi desativado, encerrar a execução com falha e
       desativar a rotina;
    3. chamar `Orquestrador.processar` com `canal=Canal.ROTINA` e
       `rotina_id=rotina.id`;
    4. fechar a execução com o status derivado do desfecho: `ENCAMINHADA`
       vira `SUCESSO`, qualquer desfecho bloqueado vira `BLOQUEADA`,
       exceção vira `FALHA`.

    O desfecho bloqueado NÃO é erro do sistema: significa que as guardas
    fizeram o trabalho delas sobre um prompt agendado. Aparece na tela de
    rotinas como tal, para que o dono corrija o enunciado.
    """
    execucao_id = str(uuid.uuid4())
    await _registrar_inicio(execucao_id, rotina.id)

    try:
        usuario = await _resolver_dono(rotina.dono_id)
        resposta = await _processar(rotina, usuario)
    except Exception as erro:
        desativar = isinstance(
            erro,
            (entra.UsuarioEntraInativo, PermissaoRotinaRevogada),
        )
        await _registrar_falha(execucao_id, rotina, erro, desativar=desativar)
        raise

    await _registrar_fim(
        execucao_id,
        status=_status_da_resposta(resposta),
        interacao_id=resposta.interacao_id,
    )
    return resposta


async def executar_agora(rotina_id: str, solicitante_id: str) -> ChatResponse:
    """Dispara uma rotina sob demanda, a partir da tela de gestão.

    Existe para que o usuário teste a rotina sem esperar a data agendada.
    Verifica que `solicitante_id` é o dono: disparar a rotina de outro
    usuário executaria sob a identidade dele, o que seria escalada de
    privilégio pela porta dos fundos.
    """
    async with fabrica_de_sessoes()() as sessao:
        rotina = await RotinaRepository(sessao).obter(rotina_id)

    if rotina is None:
        raise RotinaNaoEncontrada(f"Rotina {rotina_id} não encontrada")
    if rotina.dono_id != solicitante_id:
        raise ExecucaoNaoAutorizada("Somente o dono pode executar esta rotina")
    return await executar(rotina)


async def _registrar_inicio(execucao_id: str, rotina_id: str) -> None:
    async with fabrica_de_sessoes()() as sessao:
        await ExecucaoRepository(sessao).registrar_inicio(
            ExecucaoRotina(
                id=execucao_id,
                rotina_id=rotina_id,
                iniciada_em=datetime.now(UTC),
                concluida_em=None,
                status=StatusExecucao.EM_EXECUCAO,
            )
        )
        await sessao.commit()


async def _resolver_dono(dono_id: str) -> UsuarioAutenticado:
    identidade = await entra.consultar_usuario(dono_id)
    if identidade.oid != dono_id:
        raise entra.FalhaConsultaDiretorio("Graph devolveu identidade diferente da solicitada")

    usuario = permissoes.resolver(identidade)
    if not usuario.pode(Permissao.GERIR_ROTINAS):
        raise PermissaoRotinaRevogada("Dono sem permissão atual para executar rotinas")

    async with fabrica_de_sessoes()() as sessao:
        projetos = await UsuarioProjetoRepository(sessao).listar_projetos_do_usuario(dono_id)
        await UsuarioRepository(sessao).garantir(
            usuario_id=usuario.id,
            nome=usuario.nome,
            perfil=usuario.perfil.value,
            email=usuario.email,
        )
        await sessao.commit()

    return replace(usuario, projetos=frozenset(projetos))


async def _processar(rotina: Rotina, usuario: UsuarioAutenticado) -> ChatResponse:
    async with fabrica_de_sessoes()() as sessao:
        try:
            orquestrador = Orquestrador(
                executor=montar_executor(sessao, usuario),
                interacoes=InteracaoRepository(sessao),
                conversas=ConversaRepository(sessao),
            )
            resposta = await orquestrador.processar(
                ChatRequest(mensagem=rotina.prompt),
                usuario,
                canal=Canal.ROTINA,
                rotina_id=rotina.id,
            )
            await sessao.commit()
            return resposta
        except Exception:
            await sessao.rollback()
            raise


def _status_da_resposta(resposta: ChatResponse) -> StatusExecucao:
    if resposta.desfecho == Desfecho.ENCAMINHADA.value:
        return StatusExecucao.SUCESSO
    if resposta.desfecho == Desfecho.FALHA_EXECUTOR.value:
        return StatusExecucao.FALHA
    return StatusExecucao.BLOQUEADA


async def _registrar_fim(
    execucao_id: str,
    *,
    status: StatusExecucao,
    interacao_id: str | None,
    erro: str | None = None,
) -> None:
    async with fabrica_de_sessoes()() as sessao:
        await ExecucaoRepository(sessao).registrar_fim(
            execucao_id,
            concluida_em=datetime.now(UTC),
            status=status.value,
            interacao_id=interacao_id,
            erro=erro,
        )
        await sessao.commit()


async def _registrar_falha(
    execucao_id: str,
    rotina: Rotina,
    erro: Exception,
    *,
    desativar: bool,
) -> None:
    if isinstance(erro, (entra.UsuarioEntraInativo, PermissaoRotinaRevogada)):
        mensagem = str(erro)
    elif isinstance(erro, entra.FalhaConsultaDiretorio):
        mensagem = "Não foi possível confirmar a identidade do dono no Microsoft Entra ID"
    else:
        mensagem = "Falha interna durante a execução da rotina"

    async with fabrica_de_sessoes()() as sessao:
        if desativar and rotina.ativa:
            await RotinaRepository(sessao).atualizar(replace(rotina, ativa=False))
        await ExecucaoRepository(sessao).registrar_fim(
            execucao_id,
            concluida_em=datetime.now(UTC),
            status=StatusExecucao.FALHA.value,
            erro=mensagem,
        )
        await sessao.commit()
