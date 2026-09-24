"""Rotas das preferências e dos avisos do portfólio (Projeto.md 9.1.2.7.2, #447).

Toda rota exige sessão, e o acesso ao projeto é o da sessão **agora**
(`UsuarioAutenticado.tem_acesso_projeto`): o `perfil` gravado em `usuario`
é projeção para exibição, não fonte de autorização. Preferência de projeto
sem acesso é recusada com 403, como nas rotas de portfólio.

Nos avisos, perder o acesso a um projeto oculta também os avisos antigos
dele, das listas e das contagens. Aviso de outro usuário, de projeto sem
acesso ou fora dos 30 dias de retenção responde 404, sem distinguir o
motivo: dizer "existe, mas não é seu" revelaria o que não se pode ver.
"""

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, Query, Response, status

from app.api.deps import SessaoBanco, UsuarioAtual
from app.avisos.modelos import RETENCAO_AVISOS, Aviso
from app.avisos.repositorio import AvisoRepository, PreferenciaRepository
from app.schemas.aviso import (
    AvisoResposta,
    ContagemAvisos,
    PreferenciaPedido,
    PreferenciaResposta,
    validar_severidade,
)
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


def _aviso(aviso: Aviso) -> AvisoResposta:
    return AvisoResposta(
        id=aviso.id,
        projeto_codigo=aviso.projeto_codigo,
        event_type=aviso.event_type,
        entity_id=aviso.entity_id,
        versao=aviso.versao,
        diferencas=aviso.diferencas,
        criado_em=aviso.criado_em,
        lido_em=aviso.lido_em,
    )


def _inicio_da_retencao() -> datetime:
    return datetime.now(UTC) - RETENCAO_AVISOS


@router.get("", response_model=list[AvisoResposta])
async def listar_avisos(
    usuario: UsuarioAtual,
    banco: SessaoBanco,
    limite: Annotated[int, Query(ge=1, le=200)] = 50,
    nao_lidos: bool = False,
) -> list[AvisoResposta]:
    """Avisos do usuário nos projetos a que tem acesso, mais recentes primeiro."""
    avisos = await AvisoRepository(banco).listar(
        usuario.id,
        usuario.projetos,
        desde=_inicio_da_retencao(),
        limite=limite,
        apenas_nao_lidos=nao_lidos,
    )
    return [_aviso(a) for a in avisos]


@router.get("/contagem", response_model=ContagemAvisos)
async def contar_avisos(usuario: UsuarioAtual, banco: SessaoBanco) -> ContagemAvisos:
    """Quantos avisos visíveis ainda não foram lidos."""
    total = await AvisoRepository(banco).contar_nao_lidos(
        usuario.id, usuario.projetos, desde=_inicio_da_retencao()
    )
    return ContagemAvisos(nao_lidos=total)


@router.get("/{aviso_id}", response_model=AvisoResposta)
async def obter_aviso(aviso_id: str, usuario: UsuarioAtual, banco: SessaoBanco) -> AvisoResposta:
    aviso = await AvisoRepository(banco).obter(
        aviso_id, usuario.id, usuario.projetos, desde=_inicio_da_retencao()
    )
    if aviso is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Aviso não encontrado")
    return _aviso(aviso)


@router.post("/{aviso_id}/lido", status_code=status.HTTP_204_NO_CONTENT)
async def marcar_lido(aviso_id: str, usuario: UsuarioAtual, banco: SessaoBanco) -> Response:
    """Marca o aviso como lido; marcar de novo mantém a primeira leitura."""
    marcado = await AvisoRepository(banco).marcar_lido(
        aviso_id,
        usuario.id,
        usuario.projetos,
        desde=_inicio_da_retencao(),
        agora=datetime.now(UTC),
    )
    if not marcado:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Aviso não encontrado")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
