"""Mapeamento SQLAlchemy das tabelas do middleware.

Adaptador de persistência. O contrato de domínio continua em `models.py`,
com dataclasses puras: são elas que atravessam o orquestrador, as rotas e
os testes. Transformá-las em entidades ORM as acoplaria à sessão, e um
objeto expirado depois do commit estouraria longe do banco, num ponto
onde ninguém espera I/O.

É a mesma separação de `rag/vetorial/`: a porta de um lado, o adaptador
do outro. Aqui ficam os tipos do PostgreSQL, as restrições e os índices;
lá, o vocabulário do domínio.

A tradução entre os dois mundos acontece exclusivamente em `de_dominio` e
`to_dominio`. Concentrá-la evita que cada repositório invente a sua e que
um enum seja gravado como texto de um jeito num lugar e de outro noutro.

Sobre os vocabulários fechados: `perfil`, `canal`, `desfecho` e `status`
são `text` com `CHECK`, e não tipos enumerados do banco. `ALTER TYPE ...
ADD VALUE` não roda dentro de transação no PostgreSQL, o que tornaria
cada valor novo uma migração desconfortável; um `CHECK` se altera com
`DROP`/`ADD CONSTRAINT` comum. As listas são geradas a partir dos enums
do código (`_valores`), nunca digitadas — foi digitando que o DDL da
seção 4.4.1 do Projeto.md acabou com `'DIRETORIA'` enquanto o código
grava `'diretoria'`.

`intencao_id` fica sem chave estrangeira de propósito: o catálogo de
intenções vive em `pipeline/intencao/catalogo.py` e é artefato vivo,
revisado a cada sprint junto com `copilot/topicos.md` e o CSV de treino.
Amarrá-lo ao banco faria de cada revisão do catálogo uma migração.
"""

from datetime import datetime
from enum import Enum as EnumPython

from sqlalchemy import (
    ARRAY,
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.persistence.models import (
    Canal,
    Conversa,
    ExecucaoRotina,
    Interacao,
    Rotina,
    StatusExecucao,
    Usuario,
)
from app.pipeline.desfechos import Desfecho
from app.schemas.usuario import Perfil, Permissao

# Sem convenção de nomes, o PostgreSQL batiza as restrições sozinho e o
# `downgrade` de uma migração não encontra o que precisa remover. O nome
# curto dado a cada CheckConstraint é o `%(constraint_name)s` do molde
# abaixo: `CheckConstraint(..., name="perfil")` na tabela `usuario` vira
# `ck_usuario_perfil`.
CONVENCAO_DE_NOMES = {
    "ix": "ix_%(table_name)s_%(column_0_name)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Base declarativa. `metadata` é o alvo do autogenerate do Alembic."""

    metadata = MetaData(naming_convention=CONVENCAO_DE_NOMES)


def _valores(enum: type[EnumPython]) -> str:
    """Lista os valores de um enum como literais SQL, para o CHECK.

    Devolve `'a', 'b', 'c'`. Gerar em vez de digitar é o que garante que
    acrescentar um desfecho ao código e esquecer o banco vire erro de
    migração, e não uma linha recusada em produção.
    """
    return ", ".join(f"'{membro.value}'" for membro in enum)


# Reaproveitado por `usuario.perfil` e por `interacao.perfil`, que guardam
# o mesmo vocabulário com finalidades diferentes — ver InteracaoTabela.
_CHECK_PERFIL = f"perfil IN ({_valores(Perfil)})"


class UsuarioTabela(Base):
    """Projeção local da identidade federada do Entra ID.

    A linha é criada e atualizada pelo upsert de `UsuarioRepository`, e
    não por um cadastro: é o primeiro login que materializa o usuário
    (routes/auth.py), e cada requisição autenticada a atualiza. Quem cria
    a pessoa é o administrador do tenant, no Entra ID.

    `id` é o identificador do provedor, não uma chave interna — ver a
    docstring de `models.Usuario`.
    """

    __tablename__ = "usuario"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    nome: Mapped[str] = mapped_column(Text, nullable=False)
    # Nulo porque `UsuarioAutenticado.email` é opcional: nem todo provedor
    # devolve o endereço nas claims. O PostgreSQL aceita vários nulos sob
    # restrição de unicidade, então UNIQUE e NULL convivem aqui.
    email: Mapped[str | None] = mapped_column(Text, nullable=True, unique=True)
    perfil: Mapped[str] = mapped_column(Text, nullable=False)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    visto_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    __table_args__ = (CheckConstraint(_CHECK_PERFIL, name="perfil"),)

    @classmethod
    def de_dominio(cls, usuario: Usuario) -> "UsuarioTabela":
        return cls(
            id=usuario.id,
            nome=usuario.nome,
            email=usuario.email,
            perfil=usuario.perfil,
            criado_em=usuario.criado_em,
            visto_em=usuario.visto_em,
        )

    def to_dominio(self) -> Usuario:
        return Usuario(
            id=self.id,
            nome=self.nome,
            email=self.email,
            perfil=self.perfil,
            criado_em=self.criado_em,
            visto_em=self.visto_em,
        )


class SessaoUsuarioTabela(Base):
    """Sessão de login aberta, guardada no servidor.

    Existe para que o logout e a revogação sejam imediatos: um cookie
    autocontido continuaria valendo até expirar, mesmo depois de a pessoa
    sair ou perder o acesso. Lida e escrita só por `auth/sessao.py`.

    `id` é o SHA-256 do token que viaja no cookie, não o token. Quem ler
    esta tabela — um backup, um dump de suporte — não consegue montar um
    cookie válido a partir dela.

    `perfil` e `permissoes` são o retrato do login: valem até a sessão
    expirar, e uma mudança de grupo no tenant só chega no login seguinte.
    Nome e e-mail não se repetem aqui; vêm de `usuario` pela chave.

    `projetos` é a lista de códigos de projetos aos quais o usuário tem
    acesso, carregada no login para evitar consultas adicionais em cada
    requisição.
    """

    __tablename__ = "sessao_usuario"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    # CASCADE, e não o RESTRICT das outras tabelas: sessão não é dado de
    # auditoria, e remover um usuário deve encerrar o acesso dele junto.
    usuario_id: Mapped[str] = mapped_column(
        Text,
        ForeignKey("usuario.id", onupdate="CASCADE", ondelete="CASCADE"),
        nullable=False,
    )
    perfil: Mapped[str] = mapped_column(Text, nullable=False)
    permissoes: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, server_default=text("'{}'")
    )
    projetos: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, server_default=text("'{}'::text[]")
    )
    criada_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expira_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        CheckConstraint(_CHECK_PERFIL, name="perfil"),
        CheckConstraint(f"permissoes <@ ARRAY[{_valores(Permissao)}]::text[]", name="permissoes"),
        # Limpeza das sessões vencidas de um usuário a cada novo login.
        Index("ix_sessao_usuario_usuario", "usuario_id"),
    )


class ConversaTabela(Base):
    """Sessão de conversa, na identidade do middleware."""

    __tablename__ = "conversa"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    usuario_id: Mapped[str] = mapped_column(
        Text,
        ForeignKey("usuario.id", onupdate="CASCADE", ondelete="RESTRICT"),
        nullable=False,
    )
    # Só existe depois do primeiro turno efetivamente encaminhado: turnos
    # bloqueados não criam conversa no Copilot.
    conversa_externa_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    titulo: Mapped[str | None] = mapped_column(Text, nullable=True)
    criada_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    atualizada_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    # Arquivar em vez de excluir é decisão de rastreabilidade: o registro
    # das interações precisa sobreviver à limpeza que o usuário faz na
    # própria lista.
    arquivada_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        # Lista de histórico: as conversas de um usuário, mais recente
        # primeiro.
        Index(
            "ix_conversa_usuario_atualizada",
            "usuario_id",
            text("atualizada_em DESC"),
        ),
    )

    @classmethod
    def de_dominio(cls, conversa: Conversa) -> "ConversaTabela":
        return cls(
            id=conversa.id,
            usuario_id=conversa.usuario_id,
            conversa_externa_id=conversa.conversa_externa_id,
            titulo=conversa.titulo,
            criada_em=conversa.criada_em,
            atualizada_em=conversa.atualizada_em,
            arquivada_em=conversa.arquivada_em,
        )

    def to_dominio(self) -> Conversa:
        return Conversa(
            id=self.id,
            usuario_id=self.usuario_id,
            conversa_externa_id=self.conversa_externa_id,
            titulo=self.titulo,
            criada_em=self.criada_em,
            atualizada_em=self.atualizada_em,
            arquivada_em=self.arquivada_em,
        )


class RotinaTabela(Base):
    """Prompt pré-programado que dispara em datas planejadas.

    `timezone` é campo da rotina, e não constante do sistema: "todo dia 5
    às 8h" significa 8h no fuso de quem cadastrou, e um cron interpretado
    em UTC dispara na hora errada.
    """

    __tablename__ = "rotina"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    nome: Mapped[str] = mapped_column(Text, nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    agenda_cron: Mapped[str] = mapped_column(Text, nullable=False)
    timezone: Mapped[str] = mapped_column(Text, nullable=False)
    # A rotina executa sob a identidade e as permissões do dono,
    # resolvidas no disparo e não no cadastro.
    dono_id: Mapped[str] = mapped_column(
        Text,
        ForeignKey("usuario.id", onupdate="CASCADE", ondelete="RESTRICT"),
        nullable=False,
    )
    ativa: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    criada_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    atualizada_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    # Resultado da validação feita no cadastro. Guardá-lo permite mostrar
    # ao usuário o que a rotina vai fazer e detectar quando o catálogo
    # mudou sob os pés dela.
    intencao_prevista: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (Index("ix_rotina_dono", "dono_id"),)

    @classmethod
    def de_dominio(cls, rotina: Rotina) -> "RotinaTabela":
        return cls(
            id=rotina.id,
            nome=rotina.nome,
            prompt=rotina.prompt,
            agenda_cron=rotina.agenda_cron,
            timezone=rotina.timezone,
            dono_id=rotina.dono_id,
            ativa=rotina.ativa,
            criada_em=rotina.criada_em,
            atualizada_em=rotina.atualizada_em,
            intencao_prevista=rotina.intencao_prevista,
        )

    def to_dominio(self) -> Rotina:
        return Rotina(
            id=self.id,
            nome=self.nome,
            prompt=self.prompt,
            agenda_cron=self.agenda_cron,
            timezone=self.timezone,
            dono_id=self.dono_id,
            ativa=self.ativa,
            criada_em=self.criada_em,
            atualizada_em=self.atualizada_em,
            intencao_prevista=self.intencao_prevista,
        )


class InteracaoTabela(Base):
    """Uma interação usuário-agente, registrada para histórico e análise.

    Uma linha é gravada em TODOS os desfechos, bloqueios inclusive: as
    tentativas de ataque são o insumo do recorte de segurança do
    dashboard.

    `perfil` é redundante com `usuario.perfil` e a redundância é
    deliberada: aqui fica o perfil NO MOMENTO da interação, que é dado de
    auditoria e não pode mudar quando o usuário troca de papel; lá fica o
    último valor observado. As duas colunas respondem a perguntas
    diferentes.
    """

    __tablename__ = "interacao"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    conversa_id: Mapped[str] = mapped_column(
        Text,
        ForeignKey("conversa.id", onupdate="CASCADE", ondelete="RESTRICT"),
        nullable=False,
    )
    usuario_id: Mapped[str] = mapped_column(
        Text,
        ForeignKey("usuario.id", onupdate="CASCADE", ondelete="RESTRICT"),
        nullable=False,
    )
    perfil: Mapped[str] = mapped_column(Text, nullable=False)
    canal: Mapped[str] = mapped_column(Text, nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    resposta: Mapped[str] = mapped_column(Text, nullable=False)
    # Sem FK: o catálogo é artefato de código. Nulo quando o bloqueio
    # antecedeu a classificação.
    intencao_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    confianca_intencao: Mapped[float] = mapped_column(Float, nullable=False)
    desfecho: Mapped[str] = mapped_column(Text, nullable=False)
    latencia_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    # Tempo por etapa do pipeline, `{"injecao": 12, "executor": 1830}`.
    # Documento, e não uma coluna por etapa, porque o conjunto de etapas
    # acompanha o orquestrador: uma guarda nova não deve exigir migração
    # para passar a ser medida. JSONB no PostgreSQL; JSON genérico no
    # SQLite dos testes unitários.
    latencia_etapas: Mapped[dict[str, int] | None] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"), nullable=True
    )
    criada_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    # Preenchido quando `canal` é `rotina`. Responde "de qual rotina esta
    # mensagem nasceu"; a navegação oposta — "que interação este disparo
    # produziu" — é `execucao_rotina.interacao_id`. As duas existem
    # porque cada uma serve a uma tela, e manter só uma custaria um join
    # a mais na outra.
    rotina_id: Mapped[str | None] = mapped_column(
        Text,
        ForeignKey("rotina.id", onupdate="CASCADE", ondelete="RESTRICT"),
        nullable=True,
    )

    __table_args__ = (
        CheckConstraint(_CHECK_PERFIL, name="perfil"),
        CheckConstraint(f"canal IN ({_valores(Canal)})", name="canal"),
        CheckConstraint(f"desfecho IN ({_valores(Desfecho)})", name="desfecho"),
        # Turnos de uma conversa, em ordem cronológica (RF12).
        Index("ix_interacao_conversa_criada", "conversa_id", "criada_em"),
        # Histórico do usuário, mais recente primeiro.
        Index("ix_interacao_usuario_criada", "usuario_id", text("criada_em DESC")),
        # Janela do dashboard: nenhuma agregação varre a tabela inteira.
        Index("ix_interacao_criada_em", text("criada_em DESC")),
        # Volume por intenção.
        Index("ix_interacao_intencao_criada", "intencao_id", "criada_em"),
        # Distribuição de desfechos e série de bloqueios por guarda.
        Index("ix_interacao_desfecho_criada", "desfecho", "criada_em"),
        # Índice parcial: os enunciados sem intenção resolvida alimentam
        # tanto o backlog de novas intenções quanto o recorte de
        # segurança, e os dois casos chegam ao banco sem classificação.
        Index(
            "ix_interacao_sem_intencao",
            text("criada_em DESC"),
            postgresql_where=text("intencao_id IS NULL"),
        ),
    )

    @classmethod
    def de_dominio(cls, interacao: Interacao) -> "InteracaoTabela":
        return cls(
            id=interacao.id,
            conversa_id=interacao.conversa_id,
            usuario_id=interacao.usuario_id,
            perfil=interacao.perfil,
            canal=interacao.canal.value,
            prompt=interacao.prompt,
            resposta=interacao.resposta,
            intencao_id=interacao.intencao_id,
            confianca_intencao=interacao.confianca_intencao,
            desfecho=interacao.desfecho.value,
            latencia_ms=interacao.latencia_ms,
            criada_em=interacao.criada_em,
            rotina_id=interacao.rotina_id,
            latencia_etapas=interacao.latencia_etapas,
        )

    def to_dominio(self) -> Interacao:
        return Interacao(
            id=self.id,
            conversa_id=self.conversa_id,
            usuario_id=self.usuario_id,
            perfil=self.perfil,
            canal=Canal(self.canal),
            prompt=self.prompt,
            resposta=self.resposta,
            intencao_id=self.intencao_id,
            confianca_intencao=self.confianca_intencao,
            desfecho=Desfecho(self.desfecho),
            latencia_ms=self.latencia_ms,
            criada_em=self.criada_em,
            rotina_id=self.rotina_id,
            latencia_etapas=self.latencia_etapas,
        )


class ExecucaoRotinaTabela(Base):
    """Um disparo de rotina e seu resultado."""

    __tablename__ = "execucao_rotina"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    rotina_id: Mapped[str] = mapped_column(
        Text,
        ForeignKey("rotina.id", onupdate="CASCADE", ondelete="RESTRICT"),
        nullable=False,
    )
    iniciada_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    # Nulo enquanto o disparo não termina. É o que torna visível uma
    # rotina que travou: se a linha só pudesse ser gravada completa, um
    # disparo que nunca termina não apareceria em lugar nenhum.
    concluida_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    # Preenchido no fim, porque a interação só existe depois de o
    # pipeline rodar. Ver a ordem de gravação em rotinas/execucao.py.
    interacao_id: Mapped[str | None] = mapped_column(
        Text,
        ForeignKey("interacao.id", onupdate="CASCADE", ondelete="RESTRICT"),
        nullable=True,
    )
    erro: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        CheckConstraint(f"status IN ({_valores(StatusExecucao)})", name="status"),
        Index("ix_execucao_rotina_iniciada", "rotina_id", text("iniciada_em DESC")),
    )

    @classmethod
    def de_dominio(cls, execucao: ExecucaoRotina) -> "ExecucaoRotinaTabela":
        return cls(
            id=execucao.id,
            rotina_id=execucao.rotina_id,
            iniciada_em=execucao.iniciada_em,
            concluida_em=execucao.concluida_em,
            status=execucao.status.value,
            interacao_id=execucao.interacao_id,
            erro=execucao.erro,
        )

    def to_dominio(self) -> ExecucaoRotina:
        return ExecucaoRotina(
            id=self.id,
            rotina_id=self.rotina_id,
            iniciada_em=self.iniciada_em,
            concluida_em=self.concluida_em,
            status=StatusExecucao(self.status),
            interacao_id=self.interacao_id,
            erro=self.erro,
        )
