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

from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import UsuarioAtual, exige_permissao, obter_execucoes, obter_rotinas
from app.persistence.repository import ExecucaoRepository, RotinaRepository
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
)


@router.get("", response_model=list[RotinaResposta])
async def listar(
    usuario: UsuarioAtual,
    rotinas: Annotated[RotinaRepository, Depends(obter_rotinas)],
) -> list[RotinaResposta]:
    """Rotinas do usuário, com o próximo disparo calculado."""
    raise NotImplementedError("Gestão de rotinas a implementar na onda 5")


@router.post("/validar", response_model=ValidacaoResposta)
async def validar(pedido: RotinaRequest, usuario: UsuarioAtual) -> ValidacaoResposta:
    """Valida prompt e agenda sem salvar.

    Existe para o formulário conferir antes de gravar. Salvar uma rotina
    que já nasce inválida produziria uma execução bloqueada semanas
    depois, sem ninguém por perto para entender o motivo.
    """
    raise NotImplementedError("Validação de rotina a implementar na onda 5")


@router.post("", response_model=RotinaResposta, status_code=status.HTTP_201_CREATED)
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
    raise NotImplementedError("Gestão de rotinas a implementar na onda 5")


@router.put("/{rotina_id}", response_model=RotinaResposta)
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
    raise NotImplementedError("Gestão de rotinas a implementar na onda 5")


@router.delete("/{rotina_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remover(
    rotina_id: str,
    usuario: UsuarioAtual,
    rotinas: Annotated[RotinaRepository, Depends(obter_rotinas)],
) -> None:
    """Remove a rotina e desagenda o job correspondente.

    Remover do banco sem chamar `agendador.desagendar` deixaria um job
    órfão no jobstore, disparando uma rotina que já não existe.
    """
    raise NotImplementedError("Gestão de rotinas a implementar na onda 5")


@router.post("/{rotina_id}/executar", response_model=ExecucaoResposta)
async def executar_agora(
    rotina_id: str,
    usuario: UsuarioAtual,
    rotinas: Annotated[RotinaRepository, Depends(obter_rotinas)],
) -> ExecucaoResposta:
    """Dispara a rotina sob demanda, para o usuário testá-la.

    Executa sob a identidade do dono, como o disparo agendado. Verificar
    que o solicitante é o dono não é formalidade: disparar a rotina de
    outra pessoa executaria com as permissões dela.
    """
    raise NotImplementedError("Execução sob demanda a implementar na onda 5")


@router.get("/{rotina_id}/execucoes", response_model=list[ExecucaoResposta])
async def listar_execucoes(
    rotina_id: str,
    usuario: UsuarioAtual,
    execucoes: Annotated[ExecucaoRepository, Depends(obter_execucoes)],
    limite: int = 20,
) -> list[ExecucaoResposta]:
    """Histórico de disparos — a aba de resultados da rotina.

    É aqui que o resultado da rotina é entregue: no próprio app, sem
    depender de e-mail, Teams ou integração externa.
    """
    raise NotImplementedError("Histórico de execuções a implementar na onda 5")
