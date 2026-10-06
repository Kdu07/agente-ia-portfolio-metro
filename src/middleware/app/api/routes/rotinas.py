"""Gestão de rotinas (prompts agendados).

Todas as rotas exigem `Permissao.GERIR_ROTINAS`, aplicada no router
inteiro pela mesma razão de routes/intencoes.py: uma rota nova nasce
protegida.

Além da permissão, há uma segunda verificação em cada rota que toca uma
rotina específica: **o usuário precisa ser o dono**. Ter `GERIR_ROTINAS`
autoriza a gerir as próprias rotinas, não as dos outros — e como a
rotina executa sob a identidade do dono, editar a rotina alheia seria
escalada de privilégio disfarçada de edição.
"""

import uuid
from datetime import UTC, datetime
from typing import Annotated
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.analytics.metricas import rotulo_de_intencao
from app.api.deps import SessaoBanco, UsuarioAtual, exige_permissao, obter_execucoes, obter_rotinas
from app.auth.entra import FalhaConsultaDiretorio, UsuarioEntraInativo
from app.persistence.models import ExecucaoRotina, Interacao, Rotina
from app.persistence.repository import ExecucaoRepository, RotinaRepository
from app.rotinas import execucao as execucao_rotina
from app.rotinas.cron import criar_gatilho_cron
from app.rotinas.execucao import ExecucaoNaoAutorizada, PermissaoRotinaRevogada, RotinaNaoEncontrada
from app.rotinas.validacao import ResultadoValidacao, validar_agenda, validar_prompt
from app.schemas.erro import (
    RESPOSTA_401,
    RESPOSTA_403,
    RESPOSTA_403_DISPARO,
    RESPOSTA_404_ROTINA,
    RESPOSTA_409_ROTINA,
    RESPOSTA_422_ROTINA,
    RESPOSTA_500_EXECUCAO,
    RESPOSTA_503_ENTRA,
)
from app.schemas.rotina import (
    ExecucaoResposta,
    RotinaRequest,
    RotinaResposta,
    ValidacaoResposta,
)
from app.schemas.usuario import Permissao

router = APIRouter(
    prefix="/rotinas",
    dependencies=[Depends(exige_permissao(Permissao.GERIR_ROTINAS))],
    responses={**RESPOSTA_401, **RESPOSTA_403},
)


@router.get("", response_model=list[RotinaResposta])
async def listar(
    usuario: UsuarioAtual,
    rotinas: Annotated[RotinaRepository, Depends(obter_rotinas)],
) -> list[RotinaResposta]:
    """Rotinas do usuário, com o próximo disparo calculado."""
    return [_resposta_rotina(rotina) for rotina in await rotinas.listar_por_dono(usuario.id)]


@router.post("/validar", response_model=ValidacaoResposta)
async def validar(pedido: RotinaRequest, usuario: UsuarioAtual) -> ValidacaoResposta:
    """Valida prompt e agenda sem salvar.

    Existe para o formulário conferir antes de gravar. Salvar uma rotina
    que já nasce inválida produziria uma execução bloqueada semanas
    depois, sem ninguém por perto para entender o motivo.
    """
    resultado = await _validar_pedido(pedido)
    return ValidacaoResposta(
        valida=resultado.valida,
        intencao_prevista=resultado.intencao_prevista,
        erro=resultado.erro,
    )


@router.post(
    "",
    response_model=RotinaResposta,
    status_code=status.HTTP_201_CREATED,
    responses=RESPOSTA_422_ROTINA,
)
async def criar(
    pedido: RotinaRequest,
    usuario: UsuarioAtual,
    rotinas: Annotated[RotinaRepository, Depends(obter_rotinas)],
) -> RotinaResposta:
    """Cadastra uma rotina para o usuário autenticado.

    O dono é sempre `usuario.id` — RotinaRequest não tem campo de dono
    justamente para que o cliente não possa escolhê-lo.

    A validação de `rotinas/validacao.py` roda ANTES de gravar: prompt
    que não resolve numa intenção do catálogo resulta em 422 com a
    explicação, e nenhuma rotina é criada.
    """
    validacao = await _validar_pedido(pedido)
    _exigir_valida(validacao)
    agora = datetime.now(UTC)
    rotina = Rotina(
        id=str(uuid.uuid4()),
        nome=pedido.nome.strip(),
        prompt=pedido.prompt.strip(),
        agenda_cron=pedido.agenda_cron.strip(),
        timezone=pedido.timezone.strip(),
        dono_id=usuario.id,
        ativa=pedido.ativa,
        criada_em=agora,
        atualizada_em=agora,
        intencao_prevista=validacao.intencao_prevista,
    )
    await rotinas.criar(rotina)
    return _resposta_rotina(rotina)


@router.put(
    "/{rotina_id}",
    response_model=RotinaResposta,
    responses={**RESPOSTA_404_ROTINA, **RESPOSTA_422_ROTINA},
)
async def atualizar(
    rotina_id: str,
    pedido: RotinaRequest,
    usuario: UsuarioAtual,
    rotinas: Annotated[RotinaRepository, Depends(obter_rotinas)],
) -> RotinaResposta:
    """Edita uma rotina do próprio usuário, revalidando o prompt.

    Revalidar na edição é obrigatório: sem isso, bastaria criar uma
    rotina inócua e depois trocar o prompt para contornar a validação de
    cadastro.
    """
    existente = await _rotina_do_usuario(rotinas, rotina_id, usuario.id)
    validacao = await _validar_pedido(pedido)
    _exigir_valida(validacao)
    atualizada = Rotina(
        id=existente.id,
        nome=pedido.nome.strip(),
        prompt=pedido.prompt.strip(),
        agenda_cron=pedido.agenda_cron.strip(),
        timezone=pedido.timezone.strip(),
        dono_id=existente.dono_id,
        ativa=pedido.ativa,
        criada_em=existente.criada_em,
        atualizada_em=datetime.now(UTC),
        intencao_prevista=validacao.intencao_prevista,
    )
    await rotinas.atualizar(atualizada)
    return _resposta_rotina(atualizada)


@router.delete(
    "/{rotina_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={**RESPOSTA_404_ROTINA, **RESPOSTA_409_ROTINA},
)
async def remover(
    rotina_id: str,
    usuario: UsuarioAtual,
    rotinas: Annotated[RotinaRepository, Depends(obter_rotinas)],
) -> None:
    """Remove uma rotina que ainda não possui histórico.

    O worker reconcilia o jobstore com o PostgreSQL em até 30 segundos.
    Rotina que já disparou deve ser desativada, preservando a auditoria.
    """
    await _rotina_do_usuario(rotinas, rotina_id, usuario.id)
    try:
        await rotinas.remover(rotina_id)
    except ValueError as erro:
        raise HTTPException(status.HTTP_409_CONFLICT, str(erro)) from erro


@router.post(
    "/{rotina_id}/executar",
    response_model=ExecucaoResposta,
    responses={
        **RESPOSTA_403_DISPARO,
        **RESPOSTA_404_ROTINA,
        **RESPOSTA_500_EXECUCAO,
        **RESPOSTA_503_ENTRA,
    },
)
async def executar_agora(
    rotina_id: str,
    usuario: UsuarioAtual,
    banco: SessaoBanco,
    execucoes: Annotated[ExecucaoRepository, Depends(obter_execucoes)],
) -> ExecucaoResposta:
    """Dispara a rotina sob demanda, para o usuário testá-la.

    Executa sob a identidade do dono, como o disparo agendado. Verificar
    que o solicitante é o dono não é formalidade: disparar a rotina de
    outra pessoa executaria com as permissões dela.
    """
    # A autenticação atualizou `usuario` nesta transação. O executor confirma
    # o dono no Entra e repete o upsert em sessão própria; liberar esse lock
    # antes de aguardá-lo evita a espera circular entre as duas sessões.
    # Até aqui há apenas a projeção da identidade, sem escrita de execução.
    await banco.commit()
    try:
        resultado = await execucao_rotina.executar_agora(rotina_id, usuario.id)
    except (RotinaNaoEncontrada, ExecucaoNaoAutorizada) as erro:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Rotina não encontrada") from erro
    except (UsuarioEntraInativo, PermissaoRotinaRevogada) as erro:
        raise HTTPException(status.HTTP_403_FORBIDDEN, str(erro)) from erro
    except FalhaConsultaDiretorio as erro:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Não foi possível confirmar a identidade no Microsoft Entra ID",
        ) from erro

    registro = (
        await execucoes.obter_com_interacao(resultado.execucao_id)
        if resultado.execucao_id
        else None
    )
    if registro is None:
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "A execução terminou sem produzir registro consultável",
        )
    return _resposta_execucao(*registro)


@router.get(
    "/{rotina_id}/execucoes",
    response_model=list[ExecucaoResposta],
    responses=RESPOSTA_404_ROTINA,
)
async def listar_execucoes(
    rotina_id: str,
    usuario: UsuarioAtual,
    rotinas: Annotated[RotinaRepository, Depends(obter_rotinas)],
    execucoes: Annotated[ExecucaoRepository, Depends(obter_execucoes)],
    limite: Annotated[int, Query(ge=1, le=100)] = 20,
) -> list[ExecucaoResposta]:
    """Histórico de disparos — a aba de resultados da rotina.

    É aqui que o resultado da rotina é entregue: no próprio app, sem
    depender de e-mail, Teams ou integração externa.
    """
    await _rotina_do_usuario(rotinas, rotina_id, usuario.id)
    registros = await execucoes.listar_com_interacao_por_rotina(rotina_id, limite=limite)
    return [_resposta_execucao(execucao, interacao) for execucao, interacao in registros]


async def _validar_pedido(pedido: RotinaRequest) -> ResultadoValidacao:
    if not pedido.nome.strip():
        return ResultadoValidacao(False, erro="Informe um nome para a rotina.")
    agenda = validar_agenda(pedido.agenda_cron, pedido.timezone)
    if not agenda.valida:
        return agenda
    return await validar_prompt(pedido.prompt)


def _exigir_valida(resultado: ResultadoValidacao) -> None:
    if not resultado.valida:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, resultado.erro)


async def _rotina_do_usuario(
    repositorio: RotinaRepository,
    rotina_id: str,
    usuario_id: str,
) -> Rotina:
    rotina = await repositorio.obter(rotina_id)
    if rotina is None or rotina.dono_id != usuario_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Rotina não encontrada")
    return rotina


def _resposta_rotina(rotina: Rotina) -> RotinaResposta:
    proximo = None
    if rotina.ativa:
        gatilho = criar_gatilho_cron(
            rotina.agenda_cron,
            timezone=ZoneInfo(rotina.timezone),
        )
        proximo = gatilho.get_next_fire_time(None, datetime.now(UTC))
    return RotinaResposta(
        id=rotina.id,
        nome=rotina.nome,
        prompt=rotina.prompt,
        agenda_cron=rotina.agenda_cron,
        timezone=rotina.timezone,
        ativa=rotina.ativa,
        intencao_prevista=rotina.intencao_prevista,
        intencao_prevista_rotulo=(
            rotulo_de_intencao(rotina.intencao_prevista) if rotina.intencao_prevista else None
        ),
        proximo_disparo=proximo,
        criada_em=rotina.criada_em,
        atualizada_em=rotina.atualizada_em,
    )


def _resposta_execucao(
    execucao: ExecucaoRotina,
    interacao: Interacao | None,
) -> ExecucaoResposta:
    return ExecucaoResposta(
        id=execucao.id,
        rotina_id=execucao.rotina_id,
        iniciada_em=execucao.iniciada_em,
        concluida_em=execucao.concluida_em,
        status=execucao.status,
        resposta=interacao.resposta if interacao else None,
        desfecho=interacao.desfecho.value if interacao else None,
        erro=execucao.erro,
    )
