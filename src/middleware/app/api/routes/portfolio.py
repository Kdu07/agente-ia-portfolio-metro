"""Rotas de consulta do portfólio persistido no PostgreSQL."""

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import (
    SessaoBanco,
    UsuarioAtual,
    obter_indicadores,
    obter_marcos,
    obter_projetos,
    obter_riscos,
    obter_usuario_projeto,
)
from app.persistence.models import (
    Indicador,
    Marco,
    PapelProjeto,
    Projeto,
    Risco,
    UsuarioProjeto,
)
from app.persistence.repository_portfolio import (
    IndicadorRepository,
    MarcoRepository,
    ProjetoRepository,
    RiscoRepository,
    UsuarioProjetoRepository,
)
from app.schemas.usuario import Perfil

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


@router.get("/projetos", response_model=list[Projeto])
async def listar_projetos(
    usuario: UsuarioAtual,
    banco: SessaoBanco,
    projetos: Annotated[ProjetoRepository, Depends(obter_projetos)],
) -> list[Projeto]:
    """Lista os projetos visíveis ao usuário autenticado."""
    if usuario.perfil == Perfil.DIRETORIA:
        return await projetos.listar_todos()
    return await projetos.listar_por_usuario(usuario.id)


@router.get("/projetos/{codigo}", response_model=Projeto)
async def obter_projeto(
    codigo: str,
    usuario: UsuarioAtual,
    projetos: Annotated[ProjetoRepository, Depends(obter_projetos)],
) -> Projeto:
    if not usuario.tem_acesso_projeto(codigo):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Acesso negado ao projeto")
    projeto = await projetos.obter(codigo)
    if projeto is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Projeto não encontrado")
    return projeto


@router.get("/projetos/{codigo}/riscos", response_model=list[Risco])
async def listar_riscos(
    codigo: str,
    usuario: UsuarioAtual,
    riscos: Annotated[RiscoRepository, Depends(obter_riscos)],
) -> list[Risco]:
    if not usuario.tem_acesso_projeto(codigo):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Acesso negado ao projeto")
    return await riscos.listar_por_projeto(codigo)


@router.get("/projetos/{codigo}/marcos", response_model=list[Marco])
async def listar_marcos(
    codigo: str,
    usuario: UsuarioAtual,
    marcos: Annotated[MarcoRepository, Depends(obter_marcos)],
) -> list[Marco]:
    if not usuario.tem_acesso_projeto(codigo):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Acesso negado ao projeto")
    return await marcos.listar_por_projeto(codigo)


@router.get("/projetos/{codigo}/indicadores", response_model=list[Indicador])
async def listar_indicadores(
    codigo: str,
    usuario: UsuarioAtual,
    indicadores: Annotated[IndicadorRepository, Depends(obter_indicadores)],
) -> list[Indicador]:
    if not usuario.tem_acesso_projeto(codigo):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Acesso negado ao projeto")
    return await indicadores.listar_por_projeto(codigo)


@router.get("/marcos/vencendo", response_model=list[Marco])
async def listar_marcos_vencendo(
    usuario: UsuarioAtual,
    marcos: Annotated[MarcoRepository, Depends(obter_marcos)],
    dias: int = 7,
) -> list[Marco]:
    return [
        marco
        for marco in await marcos.listar_vencendo(dias)
        if usuario.tem_acesso_projeto(marco.projeto_codigo)
    ]


@router.get("/projetos/{codigo}/usuarios", response_model=list[str])
async def listar_usuarios_projeto(
    codigo: str,
    usuario: UsuarioAtual,
    usuarios: Annotated[UsuarioProjetoRepository, Depends(obter_usuario_projeto)],
) -> list[str]:
    if not usuario.tem_acesso_projeto(codigo):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Acesso negado ao projeto")
    return await usuarios.listar_usuarios_do_projeto(codigo)


@router.post("/projetos/{codigo}/usuarios/{usuario_id}", status_code=status.HTTP_201_CREATED)
async def adicionar_usuario_projeto(
    codigo: str,
    usuario_id: str,
    papel: PapelProjeto,
    usuario: UsuarioAtual,
    usuarios: Annotated[UsuarioProjetoRepository, Depends(obter_usuario_projeto)],
) -> UsuarioProjeto:
    if usuario.perfil not in (Perfil.DIRETORIA, Perfil.LIDER_PROJETO):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Permissão insuficiente")
    if not usuario.tem_acesso_projeto(codigo):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Acesso negado ao projeto")
    vinculo = UsuarioProjeto(
        usuario_id=usuario_id,
        projeto_codigo=codigo,
        papel=papel.value,
        criado_em=datetime.now(UTC),
    )
    await usuarios.adicionar(vinculo)
    return vinculo


@router.delete("/projetos/{codigo}/usuarios/{usuario_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remover_usuario_projeto(
    codigo: str,
    usuario_id: str,
    usuario: UsuarioAtual,
    usuarios: Annotated[UsuarioProjetoRepository, Depends(obter_usuario_projeto)],
) -> None:
    if usuario.perfil not in (Perfil.DIRETORIA, Perfil.LIDER_PROJETO):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Permissão insuficiente")
    if not usuario.tem_acesso_projeto(codigo):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Acesso negado ao projeto")
    await usuarios.remover(usuario_id, codigo)
