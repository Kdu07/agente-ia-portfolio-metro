"""Gravação e consulta das preferências e dos avisos.

Como em persistence/repository.py: nenhum método faz commit, e o controle
de acesso entra no `WHERE`. Toda leitura de aviso recebe o dono **e** os
projetos que a sessão autoriza agora: perder o acesso a um projeto oculta
também os avisos antigos dele, inclusive das contagens.
"""

from collections.abc import Collection
from datetime import datetime
from uuid import uuid4

from sqlalchemy import delete, func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.avisos.modelos import Aviso, PreferenciaAviso
from app.avisos.tabelas import AvisoTabela, PreferenciaAvisoTabela
from app.persistence.repository import _RepositorioBase
from app.persistence.tabelas import UsuarioTabela
from app.persistence.tabelas_portfolio import UsuarioProjetoTabela
from app.schemas.usuario import Perfil
from app.webhooks.modelos import TipoEventoPortfolio


class PreferenciaRepository(_RepositorioBase):
    """Adesões dos usuários aos avisos."""

    async def salvar(
        self,
        *,
        usuario_id: str,
        projeto_codigo: str,
        event_type: TipoEventoPortfolio,
        ativa: bool,
        severidade_minima: int | None,
        agora: datetime,
    ) -> None:
        valores = {"ativa": ativa, "severidade_minima": severidade_minima, "atualizada_em": agora}
        await self._sessao.execute(
            pg_insert(PreferenciaAvisoTabela)
            .values(
                usuario_id=usuario_id,
                projeto_codigo=projeto_codigo,
                event_type=event_type.value,
                **valores,
            )
            .on_conflict_do_update(
                index_elements=[
                    PreferenciaAvisoTabela.usuario_id,
                    PreferenciaAvisoTabela.projeto_codigo,
                    PreferenciaAvisoTabela.event_type,
                ],
                set_=valores,
            )
        )

    async def listar_do_usuario(
        self, usuario_id: str, projetos: Collection[str]
    ) -> list[PreferenciaAviso]:
        linhas = await self._sessao.scalars(
            select(PreferenciaAvisoTabela)
            .where(
                PreferenciaAvisoTabela.usuario_id == usuario_id,
                PreferenciaAvisoTabela.projeto_codigo.in_(list(projetos)),
            )
            .order_by(PreferenciaAvisoTabela.projeto_codigo, PreferenciaAvisoTabela.event_type)
        )
        return [linha.to_dominio() for linha in linhas]

    async def candidatas(
        self, projeto_codigo: str, event_type: TipoEventoPortfolio
    ) -> list[PreferenciaAviso]:
        """Adesões ativas ao tipo de evento do projeto, antes da checagem de acesso."""
        linhas = await self._sessao.scalars(
            select(PreferenciaAvisoTabela).where(
                PreferenciaAvisoTabela.projeto_codigo == projeto_codigo,
                PreferenciaAvisoTabela.event_type == event_type.value,
                PreferenciaAvisoTabela.ativa.is_(True),
            )
        )
        return [linha.to_dominio() for linha in linhas]


class AvisoRepository(_RepositorioBase):
    """Avisos privados, sempre filtrados por dono, projetos autorizados e retenção."""

    async def criar(
        self,
        *,
        usuario_id: str,
        projeto_codigo: str,
        source_id: str,
        event_id: str,
        event_type: TipoEventoPortfolio,
        entity_id: str,
        versao: int,
        diferencas: dict,
        agora: datetime,
    ) -> bool:
        """Cria o aviso; falso se o mesmo evento já avisou esse usuário."""
        criado = await self._sessao.scalar(
            pg_insert(AvisoTabela)
            .values(
                id=str(uuid4()),
                usuario_id=usuario_id,
                projeto_codigo=projeto_codigo,
                source_id=source_id,
                event_id=event_id,
                event_type=event_type.value,
                entity_id=entity_id,
                versao=versao,
                diferencas=diferencas,
                criado_em=agora,
            )
            .on_conflict_do_nothing(constraint="uq_aviso_evento_usuario")
            .returning(AvisoTabela.id)
        )
        return criado is not None

    def _visiveis(self, usuario_id: str, projetos: Collection[str], desde: datetime):
        return (
            AvisoTabela.usuario_id == usuario_id,
            AvisoTabela.projeto_codigo.in_(list(projetos)),
            AvisoTabela.criado_em >= desde,
        )

    async def listar(
        self,
        usuario_id: str,
        projetos: Collection[str],
        *,
        desde: datetime,
        limite: int = 50,
        apenas_nao_lidos: bool = False,
    ) -> list[Aviso]:
        consulta = select(AvisoTabela).where(*self._visiveis(usuario_id, projetos, desde))
        if apenas_nao_lidos:
            consulta = consulta.where(AvisoTabela.lido_em.is_(None))
        linhas = await self._sessao.scalars(
            consulta.order_by(AvisoTabela.criado_em.desc()).limit(limite)
        )
        return [linha.to_dominio() for linha in linhas]

    async def contar_nao_lidos(
        self, usuario_id: str, projetos: Collection[str], *, desde: datetime
    ) -> int:
        return await self._sessao.scalar(
            select(func.count())
            .select_from(AvisoTabela)
            .where(*self._visiveis(usuario_id, projetos, desde), AvisoTabela.lido_em.is_(None))
        )

    async def obter(
        self, aviso_id: str, usuario_id: str, projetos: Collection[str], *, desde: datetime
    ) -> Aviso | None:
        linha = await self._sessao.scalar(
            select(AvisoTabela).where(
                AvisoTabela.id == aviso_id, *self._visiveis(usuario_id, projetos, desde)
            )
        )
        return None if linha is None else linha.to_dominio()

    async def marcar_lido(
        self,
        aviso_id: str,
        usuario_id: str,
        projetos: Collection[str],
        *,
        desde: datetime,
        agora: datetime,
    ) -> bool:
        """Marca como lido; falso se o aviso não é visível a esse usuário."""
        resultado = await self._sessao.execute(
            update(AvisoTabela)
            .where(AvisoTabela.id == aviso_id, *self._visiveis(usuario_id, projetos, desde))
            .values(lido_em=func.coalesce(AvisoTabela.lido_em, agora))
        )
        return resultado.rowcount == 1

    async def expurgar(self, *, antes_de: datetime) -> int:
        """Remove avisos fora da retenção; devolve quantos."""

        resultado = await self._sessao.execute(
            delete(AvisoTabela).where(AvisoTabela.criado_em < antes_de)
        )
        return resultado.rowcount


async def usuarios_com_acesso(sessao, projeto_codigo: str) -> set[str]:
    """Quem pode ver o projeto agora: vínculo em `usuario_projeto` ou diretoria.

    A mesma regra que a sessão aplica no login (auth/sessao.py), para o
    consumidor, que roda sem sessão de usuário.
    """
    vinculados = await sessao.scalars(
        select(UsuarioProjetoTabela.usuario_id).where(
            UsuarioProjetoTabela.projeto_codigo == projeto_codigo
        )
    )
    diretoria = await sessao.scalars(
        select(UsuarioTabela.id).where(UsuarioTabela.perfil == Perfil.DIRETORIA.value)
    )
    return set(vinculados) | set(diretoria)
