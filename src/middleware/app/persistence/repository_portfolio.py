"""Repositórios para as tabelas do schema portfolio.

Seguem o mesmo padrão de repository.py: operações de CRUD com
transações controladas pela sessão e filtros de segurança aplicados
no SQL.
"""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.persistence.models import (
    Indicador,
    Marco,
    Projeto,
    Risco,
    UsuarioProjeto,
)
from app.persistence.tabelas_portfolio import (
    IndicadorTabela,
    MarcoTabela,
    ProjetoTabela,
    RiscoTabela,
    UsuarioProjetoTabela,
)


class _RepositorioBase:
    """Guarda a sessão. Os repositórios não a criam nem a fecham."""

    def __init__(self, sessao: AsyncSession) -> None:
        self._sessao = sessao


class ProjetoRepository(_RepositorioBase):
    """Operações sobre projetos do portfólio."""

    async def obter(self, codigo: str) -> Projeto | None:
        """Recupera um projeto pelo código."""
        resultado = await self._sessao.execute(
            select(ProjetoTabela).where(ProjetoTabela.codigo == codigo)
        )
        linha = resultado.scalar_one_or_none()
        return linha.to_dominio() if linha else None

    async def listar_por_usuario(self, usuario_id: str) -> list[Projeto]:
        """Lista projetos aos quais o usuário tem acesso."""
        resultado = await self._sessao.execute(
            select(ProjetoTabela)
            .join(UsuarioProjetoTabela, ProjetoTabela.codigo == UsuarioProjetoTabela.projeto_codigo)
            .where(UsuarioProjetoTabela.usuario_id == usuario_id)
            .order_by(ProjetoTabela.nome)
        )
        return [linha.to_dominio() for linha in resultado.scalars()]

    async def listar_todos(self) -> list[Projeto]:
        """Lista todos os projetos (para diretoria)."""
        resultado = await self._sessao.execute(
            select(ProjetoTabela).order_by(ProjetoTabela.nome)
        )
        return [linha.to_dominio() for linha in resultado.scalars()]

    async def criar(self, projeto: Projeto) -> None:
        """Cria um novo projeto."""
        self._sessao.add(ProjetoTabela.de_dominio(projeto))
        await self._sessao.flush()

    async def atualizar(self, projeto: Projeto) -> None:
        """Atualiza um projeto existente."""
        from sqlalchemy import update

        await self._sessao.execute(
            update(ProjetoTabela)
            .where(ProjetoTabela.codigo == projeto.codigo)
            .values(
                nome=projeto.nome,
                descricao=projeto.descricao,
                status=projeto.status,
                prioridade=projeto.prioridade,
                data_inicio=projeto.data_inicio,
                data_fim_prevista=projeto.data_fim_prevista,
                data_fim_real=projeto.data_fim_real,
                orcamento_aprovado=projeto.orcamento_aprovado,
                orcamento_atual=projeto.orcamento_atual,
                avanco_percentual=projeto.avanco_percentual,
                lider_id=projeto.lider_id,
                atualizado_em=datetime.now(UTC),
            )
        )


class RiscoRepository(_RepositorioBase):
    """Operações sobre riscos de projetos."""

    async def listar_por_projeto(self, projeto_codigo: str) -> list[Risco]:
        """Lista riscos de um projeto."""
        resultado = await self._sessao.execute(
            select(RiscoTabela)
            .where(RiscoTabela.projeto_codigo == projeto_codigo)
            .order_by(RiscoTabela.criado_em.desc())
        )
        return [linha.to_dominio() for linha in resultado.scalars()]

    async def criar(self, risco: Risco) -> None:
        """Cria um novo risco."""
        self._sessao.add(RiscoTabela.de_dominio(risco))
        await self._sessao.flush()

    async def atualizar(self, risco: Risco) -> None:
        """Atualiza um risco existente."""
        from sqlalchemy import update

        await self._sessao.execute(
            update(RiscoTabela)
            .where(RiscoTabela.id == risco.id)
            .values(
                descricao=risco.descricao,
                categoria=risco.categoria,
                probabilidade=risco.probabilidade,
                impacto=risco.impacto,
                status=risco.status,
                plano_mitigacao=risco.plano_mitigacao,
                atualizado_em=datetime.now(UTC),
            )
        )


class MarcoRepository(_RepositorioBase):
    """Operações sobre marcos de projetos."""

    async def listar_por_projeto(self, projeto_codigo: str) -> list[Marco]:
        """Lista marcos de um projeto."""
        resultado = await self._sessao.execute(
            select(MarcoTabela)
            .where(MarcoTabela.projeto_codigo == projeto_codigo)
            .order_by(MarcoTabela.data_prevista)
        )
        return [linha.to_dominio() for linha in resultado.scalars()]

    async def listar_vencendo(self, dias: int = 7) -> list[Marco]:
        """Lista marcos que vencem nos próximos N dias."""
        from datetime import timedelta

        data_limite = datetime.now(UTC).date() + timedelta(days=dias)
        resultado = await self._sessao.execute(
            select(MarcoTabela)
            .where(
                MarcoTabela.data_prevista <= data_limite,
                MarcoTabela.status.in_(["nao_iniciado", "em_andamento"]),
            )
            .order_by(MarcoTabela.data_prevista)
        )
        return [linha.to_dominio() for linha in resultado.scalars()]

    async def criar(self, marco: Marco) -> None:
        """Cria um novo marco."""
        self._sessao.add(MarcoTabela.de_dominio(marco))
        await self._sessao.flush()

    async def atualizar(self, marco: Marco) -> None:
        """Atualiza um marco existente."""
        from sqlalchemy import update

        await self._sessao.execute(
            update(MarcoTabela)
            .where(MarcoTabela.id == marco.id)
            .values(
                nome=marco.nome,
                descricao=marco.descricao,
                data_prevista=marco.data_prevista,
                data_real=marco.data_real,
                status=marco.status,
                atualizado_em=datetime.now(UTC),
            )
        )


class IndicadorRepository(_RepositorioBase):
    """Operações sobre indicadores de projetos."""

    async def listar_por_projeto(self, projeto_codigo: str) -> list[Indicador]:
        """Lista indicadores de um projeto."""
        resultado = await self._sessao.execute(
            select(IndicadorTabela)
            .where(IndicadorTabela.projeto_codigo == projeto_codigo)
            .order_by(IndicadorTabela.nome)
        )
        return [linha.to_dominio() for linha in resultado.scalars()]

    async def criar(self, indicador: Indicador) -> None:
        """Cria um novo indicador."""
        self._sessao.add(IndicadorTabela.de_dominio(indicador))
        await self._sessao.flush()

    async def atualizar(self, indicador: Indicador) -> None:
        """Atualiza um indicador existente."""
        from sqlalchemy import update

        await self._sessao.execute(
            update(IndicadorTabela)
            .where(IndicadorTabela.id == indicador.id)
            .values(
                nome=indicador.nome,
                descricao=indicador.descricao,
                valor_atual=indicador.valor_atual,
                valor_meta=indicador.valor_meta,
                unidade=indicador.unidade,
                data_medicao=indicador.data_medicao,
                atualizado_em=datetime.now(UTC),
            )
        )


class UsuarioProjetoRepository(_RepositorioBase):
    """Operações sobre a relação usuário-projeto."""

    async def listar_projetos_do_usuario(self, usuario_id: str) -> list[str]:
        """Lista códigos de projetos aos quais o usuário tem acesso."""
        resultado = await self._sessao.execute(
            select(UsuarioProjetoTabela.projeto_codigo)
            .where(UsuarioProjetoTabela.usuario_id == usuario_id)
        )
        return [linha[0] for linha in resultado.scalars()]

    async def listar_usuarios_do_projeto(self, projeto_codigo: str) -> list[str]:
        """Lista IDs de usuários que têm acesso ao projeto."""
        resultado = await self._sessao.execute(
            select(UsuarioProjetoTabela.usuario_id)
            .where(UsuarioProjetoTabela.projeto_codigo == projeto_codigo)
        )
        return [linha[0] for linha in resultado.scalars()]

    async def adicionar(self, usuario_projeto: UsuarioProjeto) -> None:
        """Adiciona um usuário a um projeto."""
        self._sessao.add(UsuarioProjetoTabela.de_dominio(usuario_projeto))
        await self._sessao.flush()

    async def remover(self, usuario_id: str, projeto_codigo: str) -> None:
        """Remove um usuário de um projeto."""
        from sqlalchemy import delete

        await self._sessao.execute(
            delete(UsuarioProjetoTabela).where(
                UsuarioProjetoTabela.usuario_id == usuario_id,
                UsuarioProjetoTabela.projeto_codigo == projeto_codigo,
            )
        )
