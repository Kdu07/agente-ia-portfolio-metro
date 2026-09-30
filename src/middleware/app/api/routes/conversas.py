"""Histórico de conversas do usuário.

Sem permissão especial: qualquer usuário autenticado vê o próprio
histórico. O que garante o isolamento é o filtro por `usuario_id` em
toda consulta — nunca a obscuridade do id da conversa.

Distinto do dashboard de intenções (routes/intencoes.py): lá se olha o
agregado de TODOS os usuários e por isso existe `VER_INTENCOES`; aqui
cada um vê apenas o que escreveu.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import UsuarioAtual, obter_conversas, obter_interacoes
from app.persistence.repository import ConversaRepository, InteracaoRepository
from app.schemas.conversa import ConversaDetalhe, ConversaResumo
from app.schemas.erro import RESPOSTA_401, RESPOSTA_404_CONVERSA

router = APIRouter(prefix="/conversas", responses=RESPOSTA_401)


@router.get("", response_model=list[ConversaResumo])
async def listar(
    usuario: UsuarioAtual,
    conversas: Annotated[ConversaRepository, Depends(obter_conversas)],
    incluir_arquivadas: bool = False,
) -> list[ConversaResumo]:
    """Conversas do usuário, mais recente primeiro."""
    conversas_do_usuario = await conversas.listar_com_total_por_usuario(
        usuario.id, incluir_arquivadas=incluir_arquivadas
    )
    return [
        ConversaResumo(
            id=conversa.id,
            titulo=conversa.titulo,
            criada_em=conversa.criada_em,
            atualizada_em=conversa.atualizada_em,
            total_turnos=total_turnos,
        )
        for conversa, total_turnos in conversas_do_usuario
    ]


@router.get("/{conversa_id}", response_model=ConversaDetalhe, responses=RESPOSTA_404_CONVERSA)
async def detalhar(
    conversa_id: str,
    usuario: UsuarioAtual,
    conversas: Annotated[ConversaRepository, Depends(obter_conversas)],
    interacoes: Annotated[InteracaoRepository, Depends(obter_interacoes)],
) -> ConversaDetalhe:
    """Turnos de uma conversa, para retomá-la no chat.

    Uma conversa de outro usuário resulta em 404, e não 403: confirmar
    que o id existe já entregaria informação a quem estivesse varrendo
    identificadores.
    """
    conversa = await conversas.obter(conversa_id, usuario.id)
    if conversa is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversa não encontrada")

    turnos = await interacoes.listar_por_conversa(conversa_id, usuario.id)
    return ConversaDetalhe(
        id=conversa.id,
        titulo=conversa.titulo,
        criada_em=conversa.criada_em,
        turnos=[
            {
                "id": turno.id,
                "prompt": turno.prompt,
                "resposta": turno.resposta,
                "canal": turno.canal,
                "intencao_id": turno.intencao_id,
                "desfecho": turno.desfecho.value,
                "bloqueada": turno.bloqueada,
                "criada_em": turno.criada_em,
            }
            for turno in turnos
        ],
    )


@router.delete(
    "/{conversa_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=RESPOSTA_404_CONVERSA,
)
async def arquivar(
    conversa_id: str,
    usuario: UsuarioAtual,
    conversas: Annotated[ConversaRepository, Depends(obter_conversas)],
) -> None:
    """Arquiva a conversa, sem apagar as interações.

    O verbo HTTP é DELETE porque é o que o usuário percebe — a conversa
    some da lista dele. Mas o registro sobrevive: apagar interações
    quebraria a rastreabilidade (RNF02) e abriria um caminho para apagar
    a própria trilha depois de um bloqueio.
    """
    if await conversas.obter(conversa_id, usuario.id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversa não encontrada")
    await conversas.arquivar(conversa_id, usuario.id)
