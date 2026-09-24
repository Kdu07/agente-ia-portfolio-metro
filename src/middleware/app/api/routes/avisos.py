"""Rotas das preferências e dos avisos do portfólio (Projeto.md 9.1.2.7.2, #447).

Toda rota exige sessão, e o acesso ao projeto é o da sessão **agora**
(`UsuarioAutenticado.tem_acesso_projeto`): o `perfil` gravado em `usuario`
é projeção para exibição, não fonte de autorização. Preferência de projeto
sem acesso é recusada com 403, como nas rotas de portfólio.
"""

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, status

from app.api.deps import SessaoBanco, UsuarioAtual
from app.avisos.repositorio import PreferenciaRepository
from app.schemas.aviso import PreferenciaPedido, PreferenciaResposta, validar_severidade
from app.webhooks.modelos import TipoEventoPortfolio

router = APIRouter(prefix="/avisos", tags=["avisos"])

TipoEvento = Annotated[TipoEventoPortfolio, Path(description="Tipo de evento do portfólio")]


def _resposta(preferencia) -> PreferenciaResposta:
    return PreferenciaResposta(
        projeto_codigo=preferencia.projeto_codigo,
        event_type=preferencia.event_type,
        ativa=preferencia.ativa,
        severidade_minima=preferencia.severidade_minima,
        atualizada_em=preferencia.atualizada_em,
    )


@router.get("/preferencias", response_model=list[PreferenciaResposta])
async def listar_preferencias(
    usuario: UsuarioAtual, banco: SessaoBanco
) -> list[PreferenciaResposta]:
    """Preferências salvas nos projetos a que o usuário tem acesso.

    Projeto e tipo sem preferência salva estão desativados: o padrão é não
    avisar, sem inscrição automática.
    """
    preferencias = await PreferenciaRepository(banco).listar_do_usuario(
        usuario.id, usuario.projetos
    )
    return [_resposta(p) for p in preferencias]


@router.put("/preferencias/{projeto_codigo}/{event_type}", response_model=PreferenciaResposta)
async def salvar_preferencia(
    projeto_codigo: str,
    event_type: TipoEvento,
    pedido: PreferenciaPedido,
    usuario: UsuarioAtual,
    banco: SessaoBanco,
) -> PreferenciaResposta:
    """Liga, desliga ou ajusta a severidade mínima de um tipo de aviso.

    Ativar não gera aviso retroativo: só alterações aplicadas depois.
    """
    if not usuario.tem_acesso_projeto(projeto_codigo):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Acesso negado ao projeto")
    try:
        validar_severidade(event_type, pedido.severidade_minima)
    except ValueError:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "severidade_minima só se aplica a risco.alterado",
        ) from None
    preferencias = PreferenciaRepository(banco)
    await preferencias.salvar(
        usuario_id=usuario.id,
        projeto_codigo=projeto_codigo,
        event_type=event_type,
        ativa=pedido.ativa,
        severidade_minima=pedido.severidade_minima,
        agora=datetime.now(UTC),
    )
    [salva] = [
        p
        for p in await preferencias.listar_do_usuario(usuario.id, {projeto_codigo})
        if p.event_type is event_type
    ]
    return _resposta(salva)
