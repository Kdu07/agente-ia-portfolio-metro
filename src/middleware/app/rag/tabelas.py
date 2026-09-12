"""Esquema `rag`: registro da ingestão e texto dos trechos indexados.

O índice vetorial guarda vetor, identificador e os três campos de filtro
— nunca o texto (invariante 1 de `rag/vetorial/base.py`). O texto mora
aqui, e é lido pelo `trecho_id` depois da busca.

Schema próprio, e não o `public`, pela razão da base estruturada (seção
3.6 do plano): deixar visível que é dado do caminho alternativo, e não o
registro operacional do middleware.

- `rag.arquivo`: uma linha por arquivo que a fonte já listou, com o
  destino que ele teve (`situacao`) e por quê. É o que torna a ingestão
  auditável — "este arquivo não está no índice porque foi substituído
  pela v3" é uma linha, não um silêncio;
- `rag.trecho`: o texto de cada trecho indexado, exatamente o que foi
  vetorizado, com a permissão que foi para o índice.

A tabela do adaptador pgvector (`rag.trecho_vetor`) não está aqui: exige
a extensão `vector`, que a imagem `postgres:16-alpine` do compose não
tem. Entra na migração que trocar a imagem, se a reserva for acionada.
"""

from datetime import date, datetime
from typing import Any

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Index, Integer, Text, text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

# `_valores` é o gerador de `CHECK` a partir de enum de persistence/: o
# mesmo mecanismo, para que um perfil novo no código não possa ser
# esquecido no banco.
from app.persistence.tabelas import Base, _valores
from app.rag.ingestao.modelos import SituacaoArquivo
from app.schemas.usuario import Perfil

ESQUEMA = "rag"

# Os perfis gravados são sempre valores do enum do código. Conferido no
# banco porque é o campo que decide quem lê o trecho.
_CHECK_PERFIS = f"perfis <@ ARRAY[{_valores(Perfil)}]::text[]"


class ArquivoTabela(Base):
    """Um arquivo da fonte e o destino que a ingestão lhe deu."""

    __tablename__ = "arquivo"

    # Identificador na fonte (id do Drive). Estável a renomeações: um
    # arquivo renomeado continua sendo o mesmo arquivo.
    origem_id: Mapped[str] = mapped_column(Text, primary_key=True)
    nome: Mapped[str] = mapped_column(Text, nullable=False)
    mime: Mapped[str] = mapped_column(Text, nullable=False)
    md5: Mapped[str | None] = mapped_column(Text, nullable=True)
    modificado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    link: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Ficha: nulos quando o arquivo não foi identificado.
    documento_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    codigo: Mapped[str | None] = mapped_column(Text, nullable=True)
    tipo: Mapped[str | None] = mapped_column(Text, nullable=True)
    versao: Mapped[int | None] = mapped_column(Integer, nullable=True)
    periodo: Mapped[str | None] = mapped_column(Text, nullable=True)
    data_referencia: Mapped[date | None] = mapped_column(Date, nullable=True)
    projeto: Mapped[str | None] = mapped_column(Text, nullable=True)
    classificacao: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Permissão efetiva do documento. Nula no consolidado do portfólio,
    # em que cada linha tem a sua (ver `rag.trecho.perfis`).
    perfis: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)
    situacao: Mapped[str] = mapped_column(Text, nullable=False)
    motivo: Mapped[str | None] = mapped_column(Text, nullable=True)
    observacoes: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, server_default=text("'{}'::text[]")
    )
    # A ficha completa, para que uma execução em que o arquivo não mudou
    # não precise baixá-lo de novo para saber o que ele é.
    metadados: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    # md5 + versão do pipeline + permissão + contexto. Diferente da
    # calculada na execução, o documento é reindexado (ver indexacao.py).
    assinatura: Mapped[str | None] = mapped_column(Text, nullable=True)
    total_trechos: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    visto_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    indexado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint(f"situacao IN ({_valores(SituacaoArquivo)})", name="situacao"),
        CheckConstraint(_CHECK_PERFIS, name="perfis"),
        # No máximo um arquivo indexado por documento lógico: duas versões
        # do mesmo termo no índice ao mesmo tempo seria exatamente a
        # contradição que a resolução de vigência existe para evitar.
        Index(
            "ix_arquivo_documento_indexado",
            "documento_id",
            unique=True,
            postgresql_where=text("situacao = 'indexado'"),
        ),
        {"schema": ESQUEMA},
    )


class TrechoTabela(Base):
    """Texto de um trecho indexado, lido pelo `trecho_id` depois da busca."""

    __tablename__ = "trecho"

    trecho_id: Mapped[str] = mapped_column(Text, primary_key=True)
    documento_id: Mapped[str] = mapped_column(Text, nullable=False)
    origem_id: Mapped[str] = mapped_column(
        Text,
        ForeignKey(f"{ESQUEMA}.arquivo.origem_id", onupdate="CASCADE", ondelete="RESTRICT"),
        nullable=False,
    )
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    texto: Mapped[str] = mapped_column(Text, nullable=False)
    tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    # Seção, aba ou slide: o que a citação vai mostrar ao usuário.
    localizador: Mapped[str] = mapped_column(Text, nullable=False)
    projeto: Mapped[str | None] = mapped_column(Text, nullable=True)
    perfis: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False)

    __table_args__ = (
        CheckConstraint(_CHECK_PERFIS, name="perfis"),
        # Reindexar e retirar um documento apagam por aqui.
        Index("ix_trecho_documento", "documento_id"),
        {"schema": ESQUEMA},
    )
