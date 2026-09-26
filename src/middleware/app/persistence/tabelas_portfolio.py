"""Mapeamento SQLAlchemy das tabelas do schema portfolio.

Adaptador de persistência para os dados estruturados do portfólio.
Segue o mesmo padrão de tabelas.py: modelos de domínio em models.py,
adaptação ORM aqui, e tradução em de_dominio/to_dominio.
"""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Index,
    Integer,
    MetaData,
    Numeric,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.persistence.models import (
    Indicador,
    Marco,
    PapelProjeto,
    Prioridade,
    Projeto,
    Risco,
    StatusMarco,
    StatusProjeto,
    StatusRisco,
    UsuarioProjeto,
)


class Base(DeclarativeBase):
    """Base declarativa. `metadata` é o alvo do autogenerate do Alembic."""

    metadata = MetaData(
        naming_convention={
            "ix": "ix_%(table_name)s_%(column_0_name)s",
            "uq": "uq_%(table_name)s_%(column_0_name)s",
            "ck": "ck_%(table_name)s_%(constraint_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s",
        }
    )


def _valores(enum) -> str:
    """Lista os valores de um enum como literais SQL, para o CHECK."""
    return ", ".join(f"'{membro.value}'" for membro in enum)


_STATUS_PROJETO = f"status IN ({_valores(StatusProjeto)})"
_PRIORIDADE = f"prioridade IN ({_valores(Prioridade)})"
_STATUS_RISCO = f"status IN ({_valores(StatusRisco)})"
_STATUS_MARCO = f"status IN ({_valores(StatusMarco)})"
_PAPEL_PROJETO = f"papel IN ({_valores(PapelProjeto)})"


class ProjetoTabela(Base):
    """Tabela de projetos do portfólio."""

    __tablename__ = "projeto"

    codigo: Mapped[str] = mapped_column(Text, primary_key=True)
    nome: Mapped[str] = mapped_column(Text, nullable=False)
    descricao: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    prioridade: Mapped[str] = mapped_column(Text, nullable=False)
    data_inicio: Mapped[date | None] = mapped_column(Date, nullable=True)
    data_fim_prevista: Mapped[date | None] = mapped_column(Date, nullable=True)
    data_fim_real: Mapped[date | None] = mapped_column(Date, nullable=True)
    orcamento_aprovado: Mapped[Decimal | None] = mapped_column(Numeric(15, 2), nullable=True)
    orcamento_atual: Mapped[Decimal | None] = mapped_column(Numeric(15, 2), nullable=True)
    avanco_percentual: Mapped[int] = mapped_column(Integer, nullable=False)
    lider_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    atualizado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        CheckConstraint(_STATUS_PROJETO, name="ck_projeto_status"),
        CheckConstraint(_PRIORIDADE, name="ck_projeto_prioridade"),
        CheckConstraint("avanco_percentual >= 0 AND avanco_percentual <= 100", name="ck_projeto_avanco"),
        Index("ix_projeto_status", "status"),
        Index("ix_projeto_lider", "lider_id"),
        {"schema": "portfolio"},
    )

    @classmethod
    def de_dominio(cls, projeto: Projeto) -> "ProjetoTabela":
        return cls(
            codigo=projeto.codigo,
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
            criado_em=projeto.criado_em,
            atualizado_em=projeto.atualizado_em,
        )

    def to_dominio(self) -> Projeto:
        return Projeto(
            codigo=self.codigo,
            nome=self.nome,
            descricao=self.descricao,
            status=self.status,
            prioridade=self.prioridade,
            data_inicio=self.data_inicio,
            data_fim_prevista=self.data_fim_prevista,
            data_fim_real=self.data_fim_real,
            orcamento_aprovado=self.orcamento_aprovado,
            orcamento_atual=self.orcamento_atual,
            avanco_percentual=self.avanco_percentual,
            lider_id=self.lider_id,
            criado_em=self.criado_em,
            atualizado_em=self.atualizado_em,
        )


class RiscoTabela(Base):
    """Tabela de riscos de projetos."""

    __tablename__ = "risco"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    projeto_codigo: Mapped[str] = mapped_column(Text, nullable=False)
    descricao: Mapped[str] = mapped_column(Text, nullable=False)
    categoria: Mapped[str | None] = mapped_column(Text, nullable=True)
    probabilidade: Mapped[int] = mapped_column(Integer, nullable=False)
    impacto: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    plano_mitigacao: Mapped[str | None] = mapped_column(Text, nullable=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    atualizado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        CheckConstraint("probabilidade >= 1 AND probabilidade <= 5", name="ck_risco_probabilidade"),
        CheckConstraint("impacto >= 1 AND impacto <= 5", name="ck_risco_impacto"),
        CheckConstraint(_STATUS_RISCO, name="ck_risco_status"),
        Index("ix_risco_projeto", "projeto_codigo"),
        Index("ix_risco_status", "status"),
        {"schema": "portfolio"},
    )

    @classmethod
    def de_dominio(cls, risco: Risco) -> "RiscoTabela":
        return cls(
            id=risco.id,
            projeto_codigo=risco.projeto_codigo,
            descricao=risco.descricao,
            categoria=risco.categoria,
            probabilidade=risco.probabilidade,
            impacto=risco.impacto,
            status=risco.status,
            plano_mitigacao=risco.plano_mitigacao,
            criado_em=risco.criado_em,
            atualizado_em=risco.atualizado_em,
        )

    def to_dominio(self) -> Risco:
        return Risco(
            id=self.id,
            projeto_codigo=self.projeto_codigo,
            descricao=self.descricao,
            categoria=self.categoria,
            probabilidade=self.probabilidade,
            impacto=self.impacto,
            status=self.status,
            plano_mitigacao=self.plano_mitigacao,
            criado_em=self.criado_em,
            atualizado_em=self.atualizado_em,
        )


class MarcoTabela(Base):
    """Tabela de marcos de projetos."""

    __tablename__ = "marco"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    projeto_codigo: Mapped[str] = mapped_column(Text, nullable=False)
    nome: Mapped[str] = mapped_column(Text, nullable=False)
    descricao: Mapped[str | None] = mapped_column(Text, nullable=True)
    data_prevista: Mapped[date] = mapped_column(Date, nullable=False)
    data_real: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    atualizado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        CheckConstraint(_STATUS_MARCO, name="ck_marco_status"),
        Index("ix_marco_projeto", "projeto_codigo"),
        Index("ix_marco_data_prevista", "data_prevista"),
        {"schema": "portfolio"},
    )

    @classmethod
    def de_dominio(cls, marco: Marco) -> "MarcoTabela":
        return cls(
            id=marco.id,
            projeto_codigo=marco.projeto_codigo,
            nome=marco.nome,
            descricao=marco.descricao,
            data_prevista=marco.data_prevista,
            data_real=marco.data_real,
            status=marco.status,
            criado_em=marco.criado_em,
            atualizado_em=marco.atualizado_em,
        )

    def to_dominio(self) -> Marco:
        return Marco(
            id=self.id,
            projeto_codigo=self.projeto_codigo,
            nome=self.nome,
            descricao=self.descricao,
            data_prevista=self.data_prevista,
            data_real=self.data_real,
            status=self.status,
            criado_em=self.criado_em,
            atualizado_em=self.atualizado_em,
        )


class IndicadorTabela(Base):
    """Tabela de indicadores de projetos."""

    __tablename__ = "indicador"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    projeto_codigo: Mapped[str] = mapped_column(Text, nullable=False)
    nome: Mapped[str] = mapped_column(Text, nullable=False)
    descricao: Mapped[str | None] = mapped_column(Text, nullable=True)
    valor_atual: Mapped[Decimal | None] = mapped_column(Numeric(15, 2), nullable=True)
    valor_meta: Mapped[Decimal | None] = mapped_column(Numeric(15, 2), nullable=True)
    unidade: Mapped[str | None] = mapped_column(Text, nullable=True)
    data_medicao: Mapped[date | None] = mapped_column(Date, nullable=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    atualizado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        Index("ix_indicador_projeto", "projeto_codigo"),
        {"schema": "portfolio"},
    )

    @classmethod
    def de_dominio(cls, indicador: Indicador) -> "IndicadorTabela":
        return cls(
            id=indicador.id,
            projeto_codigo=indicador.projeto_codigo,
            nome=indicador.nome,
            descricao=indicador.descricao,
            valor_atual=indicador.valor_atual,
            valor_meta=indicador.valor_meta,
            unidade=indicador.unidade,
            data_medicao=indicador.data_medicao,
            criado_em=indicador.criado_em,
            atualizado_em=indicador.atualizado_em,
        )

    def to_dominio(self) -> Indicador:
        return Indicador(
            id=self.id,
            projeto_codigo=self.projeto_codigo,
            nome=self.nome,
            descricao=self.descricao,
            valor_atual=self.valor_atual,
            valor_meta=self.valor_meta,
            unidade=self.unidade,
            data_medicao=self.data_medicao,
            criado_em=self.criado_em,
            atualizado_em=self.atualizado_em,
        )


class UsuarioProjetoTabela(Base):
    """Tabela de relação usuário-projeto."""

    __tablename__ = "usuario_projeto"

    usuario_id: Mapped[str] = mapped_column(Text, primary_key=True)
    projeto_codigo: Mapped[str] = mapped_column(Text, primary_key=True)
    papel: Mapped[str] = mapped_column(Text, nullable=False)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        CheckConstraint(_PAPEL_PROJETO, name="ck_usuario_projeto_papel"),
        Index("ix_usuario_projeto_usuario", "usuario_id"),
        Index("ix_usuario_projeto_projeto", "projeto_codigo"),
        {"schema": "portfolio"},
    )

    @classmethod
    def de_dominio(cls, usuario_projeto: UsuarioProjeto) -> "UsuarioProjetoTabela":
        return cls(
            usuario_id=usuario_projeto.usuario_id,
            projeto_codigo=usuario_projeto.projeto_codigo,
            papel=usuario_projeto.papel,
            criado_em=usuario_projeto.criado_em,
        )

    def to_dominio(self) -> UsuarioProjeto:
        return UsuarioProjeto(
            usuario_id=self.usuario_id,
            projeto_codigo=self.projeto_codigo,
            papel=self.papel,
            criado_em=self.criado_em,
        )
