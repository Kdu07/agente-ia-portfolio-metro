"""Rotas da API para gerenciamento do portfólio de projetos.

Fornece endpoints para CRUD de projetos, riscos, marcos, indicadores e
gerenciamento de acesso por projeto. Todas as rotas exigem autenticação e
aplicam controle de acesso por projeto quando necessário.
"""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    SessaoBanco,
    UsuarioAtual,
    exige_permissao,
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
from app.schemas.usuario import Perfil

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


# === Projetos ===


@router.get("/projetos")
async def listar_projetos(
    usuario: UsuarioAtual,
    banco: SessaoBanco,
    projetos_repo: Annotated[object, Depends(obter_projetos)],
) -> list[Projeto]:
    """Lista projetos do usuário ou todos se for diretoria."""
    if usuario.perfil == Perfil.DIRETORIA:
        return await projetos_repo.listar_todos()
    return await projetos_repo.listar_por_usuario(usuario.id)


@router.get("/projetos/{codigo}")
async def obter_projeto(
    codigo: str,
    usuario: UsuarioAtual,
    banco: SessaoBanco,
    projetos_repo: Annotated[object, Depends(obter_projetos)],
) -> Projeto:
    """Recupera um projeto específico."""
    if not usuario.tem_acesso_projeto(codigo):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            f"Usuário não tem acesso ao projeto {codigo}",
        )

    projeto = await projetos_repo.obter(codigo)
    if projeto is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Projeto não encontrado")
    return projeto


@router.post("/projetos", status_code=status.HTTP_201_CREATED)
async def criar_projeto(
    projeto: Projeto,
    usuario: UsuarioAtual,
    banco: SessaoBanco,
    projetos_repo: Annotated[object, Depends(obter_projetos)],
    usuario_projeto_repo: Annotated[object, Depends(obter_usuario_projeto)],
) -> Projeto:
    """Cria um novo projeto. Requer perfil de liderança ou diretoria."""
    if usuario.perfil not in (Perfil.DIRETORIA, Perfil.LIDER_PROJETO):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Apenas liderança e diretoria podem criar projetos",
        )

    projeto.criado_em = datetime.now(UTC)
    projeto.atualizado_em = datetime.now(UTC)

    await projetos_repo.criar(projeto)

    # O criador é automaticamente líder do projeto
    if projeto.lider_id is None:
        projeto.lider_id = usuario.id

    await usuario_projeto_repo.adicionar(
        UsuarioProjeto(
            usuario_id=usuario.id,
            projeto_codigo=projeto.codigo,
            papel=PapelProjeto.LIDER.value,
            criado_em=datetime.now(UTC),
        )
    )

    return projeto


@router.put("/projetos/{codigo}")
async def atualizar_projeto(
    codigo: str,
    projeto: Projeto,
    usuario: UsuarioAtual,
    banco: SessaoBanco,
    projetos_repo: Annotated[object, Depends(obter_projetos)],
) -> Projeto:
    """Atualiza um projeto existente. Requer acesso ao projeto."""
    if not usuario.tem_acesso_projeto(codigo):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            f"Usuário não tem acesso ao projeto {codigo}",
        )

    projeto.codigo = codigo
    projeto.atualizado_em = datetime.now(UTC)

    await projetos_repo.atualizar(projeto)
    return projeto


# === Riscos ===


@router.get("/projetos/{codigo}/riscos")
async def listar_riscos(
    codigo: str,
    usuario: UsuarioAtual,
    banco: SessaoBanco,
    riscos_repo: Annotated[object, Depends(obter_riscos)],
) -> list[Risco]:
    """Lista riscos de um projeto."""
    if not usuario.tem_acesso_projeto(codigo):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            f"Usuário não tem acesso ao projeto {codigo}",
        )

    return await riscos_repo.listar_por_projeto(codigo)


@router.post("/projetos/{codigo}/riscos", status_code=status.HTTP_201_CREATED)
async def criar_risco(
    codigo: str,
    risco: Risco,
    usuario: UsuarioAtual,
    banco: SessaoBanco,
    riscos_repo: Annotated[object, Depends(obter_riscos)],
) -> Risco:
    """Cria um novo risco para um projeto."""
    if not usuario.tem_acesso_projeto(codigo):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            f"Usuário não tem acesso ao projeto {codigo}",
        )

    risco.projeto_codigo = codigo
    risco.criado_em = datetime.now(UTC)
    risco.atualizado_em = datetime.now(UTC)

    await riscos_repo.criar(risco)
    return risco


@router.put("/riscos/{risco_id}")
async def atualizar_risco(
    risco_id: str,
    risco: Risco,
    usuario: UsuarioAtual,
    banco: SessaoBanco,
    riscos_repo: Annotated[object, Depends(obter_riscos)],
) -> Risco:
    """Atualiza um risco existente."""
    if not usuario.tem_acesso_projeto(risco.projeto_codigo):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            f"Usuário não tem acesso ao projeto {risco.projeto_codigo}",
        )

    risco.id = risco_id
    risco.atualizado_em = datetime.now(UTC)

    await riscos_repo.atualizar(risco)
    return risco


# === Marcos ===


@router.get("/projetos/{codigo}/marcos")
async def listar_marcos(
    codigo: str,
    usuario: UsuarioAtual,
    banco: SessaoBanco,
    marcos_repo: Annotated[object, Depends(obter_marcos)],
) -> list[Marco]:
    """Lista marcos de um projeto."""
    if not usuario.tem_acesso_projeto(codigo):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            f"Usuário não tem acesso ao projeto {codigo}",
        )

    return await marcos_repo.listar_por_projeto(codigo)


@router.get("/marcos/vencendo")
async def listar_marcos_vencendo(
    usuario: UsuarioAtual,
    banco: SessaoBanco,
    marcos_repo: Annotated[object, Depends(obter_marcos)],
    dias: int = 7,
) -> list[Marco]:
    """Lista marcos que vencem nos próximos N dias."""
    marcos = await marcos_repo.listar_vencendo(dias)

    # Filtrar apenas projetos que o usuário tem acesso
    return [m for m in marcos if usuario.tem_acesso_projeto(m.projeto_codigo)]


@router.post("/projetos/{codigo}/marcos", status_code=status.HTTP_201_CREATED)
async def criar_marco(
    codigo: str,
    marco: Marco,
    usuario: UsuarioAtual,
    banco: SessaoBanco,
    marcos_repo: Annotated[object, Depends(obter_marcos)],
) -> Marco:
    """Cria um novo marco para um projeto."""
    if not usuario.tem_acesso_projeto(codigo):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            f"Usuário não tem acesso ao projeto {codigo}",
        )

    marco.projeto_codigo = codigo
    marco.criado_em = datetime.now(UTC)
    marco.atualizado_em = datetime.now(UTC)

    await marcos_repo.criar(marco)
    return marco


@router.put("/marcos/{marco_id}")
async def atualizar_marco(
    marco_id: str,
    marco: Marco,
    usuario: UsuarioAtual,
    banco: SessaoBanco,
    marcos_repo: Annotated[object, Depends(obter_marcos)],
) -> Marco:
    """Atualiza um marco existente."""
    if not usuario.tem_acesso_projeto(marco.projeto_codigo):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            f"Usuário não tem acesso ao projeto {marco.projeto_codigo}",
        )

    marco.id = marco_id
    marco.atualizado_em = datetime.now(UTC)

    await marcos_repo.atualizar(marco)
    return marco


# === Indicadores ===


@router.get("/projetos/{codigo}/indicadores")
async def listar_indicadores(
    codigo: str,
    usuario: UsuarioAtual,
    banco: SessaoBanco,
    indicadores_repo: Annotated[object, Depends(obter_indicadores)],
) -> list[Indicador]:
    """Lista indicadores de um projeto."""
    if not usuario.tem_acesso_projeto(codigo):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            f"Usuário não tem acesso ao projeto {codigo}",
        )

    return await indicadores_repo.listar_por_projeto(codigo)


@router.post("/projetos/{codigo}/indicadores", status_code=status.HTTP_201_CREATED)
async def criar_indicador(
    codigo: str,
    indicador: Indicador,
    usuario: UsuarioAtual,
    banco: SessaoBanco,
    indicadores_repo: Annotated[object, Depends(obter_indicadores)],
) -> Indicador:
    """Cria um novo indicador para um projeto."""
    if not usuario.tem_acesso_projeto(codigo):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            f"Usuário não tem acesso ao projeto {codigo}",
        )

    indicador.projeto_codigo = codigo
    indicador.criado_em = datetime.now(UTC)
    indicador.atualizado_em = datetime.now(UTC)

    await indicadores_repo.criar(indicador)
    return indicador


@router.put("/indicadores/{indicador_id}")
async def atualizar_indicador(
    indicador_id: str,
    indicador: Indicador,
    usuario: UsuarioAtual,
    banco: SessaoBanco,
    indicadores_repo: Annotated[object, Depends(obter_indicadores)],
) -> Indicador:
    """Atualiza um indicador existente."""
    if not usuario.tem_acesso_projeto(indicador.projeto_codigo):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            f"Usuário não tem acesso ao projeto {indicador.projeto_codigo}",
        )

    indicador.id = indicador_id
    indicador.atualizado_em = datetime.now(UTC)

    await indicadores_repo.atualizar(indicador)
    return indicador


# === Usuário-Projeto ===


@router.get("/projetos/{codigo}/usuarios")
async def listar_usuarios_projeto(
    codigo: str,
    usuario: UsuarioAtual,
    banco: SessaoBanco,
    usuario_projeto_repo: Annotated[object, Depends(obter_usuario_projeto)],
) -> list[str]:
    """Lista IDs de usuários com acesso ao projeto."""
    if not usuario.tem_acesso_projeto(codigo):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            f"Usuário não tem acesso ao projeto {codigo}",
        )

    return await usuario_projeto_repo.listar_usuarios_do_projeto(codigo)


@router.post("/projetos/{codigo}/usuarios/{usuario_id}", status_code=status.HTTP_201_CREATED)
async def adicionar_usuario_projeto(
    codigo: str,
    usuario_id: str,
    papel: PapelProjeto,
    usuario: UsuarioAtual,
    banco: SessaoBanco,
    usuario_projeto_repo: Annotated[object, Depends(obter_usuario_projeto)],
) -> UsuarioProjeto:
    """Adiciona um usuário a um projeto. Requer perfil de liderança."""
    if usuario.perfil not in (Perfil.DIRETORIA, Perfil.LIDER_PROJETO):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Apenas liderança e diretoria podem gerir acesso a projetos",
        )

    if not usuario.tem_acesso_projeto(codigo):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            f"Usuário não tem acesso ao projeto {codigo}",
        )

    usuario_projeto = UsuarioProjeto(
        usuario_id=usuario_id,
        projeto_codigo=codigo,
        papel=papel.value,
        criado_em=datetime.now(UTC),
    )

    await usuario_projeto_repo.adicionar(usuario_projeto)
    return usuario_projeto


@router.delete("/projetos/{codigo}/usuarios/{usuario_id}")
async def remover_usuario_projeto(
    codigo: str,
    usuario_id: str,
    usuario: UsuarioAtual,
    banco: SessaoBanco,
    usuario_projeto_repo: Annotated[object, Depends(obter_usuario_projeto)],
) -> None:
    """Remove um usuário de um projeto. Requer perfil de liderança."""
    if usuario.perfil not in (Perfil.DIRETORIA, Perfil.LIDER_PROJETO):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Apenas liderança e diretoria podem gerir acesso a projetos",
        )

    if not usuario.tem_acesso_projeto(codigo):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            f"Usuário não tem acesso ao projeto {codigo}",
        )

    await usuario_projeto_repo.remover(usuario_id, codigo)
