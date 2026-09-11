"""Gravação e consulta dos registros do middleware.

Interface de persistência usada pelo orquestrador, pelas rotas e pelo
agendador, implementada com SQLAlchemy 2 assíncrono sobre PostgreSQL
(ver infra/docker-compose.yml).

Divisão dos repositórios por agregado, e não por tabela:
`InteracaoRepository` concentra tudo o que se lê e escreve sobre
interações, incluindo o histórico; as agregações do dashboard ficam em
`analytics/consultas.py`, porque as perguntas da análise mudam com muito
mais frequência que o esquema e não devem arrastar este módulo junto.

**Sobre o commit.** Nenhum método aqui faz commit. Quem fecha a
transação é `sessao.obter_sessao` no fim da requisição, ou o chamador que
abriu a sessão. É o que permite gravar a conversa e a interação de um
mesmo turno numa transação só: um erro no meio não deixa metade gravada.

**Sobre o controle de acesso.** Onde há `usuario_id` na assinatura, ele
entra no `WHERE` da consulta e não num filtro em Python depois. A
diferença importa: filtrar depois significa que o banco já devolveu o
dado de outra pessoa, e basta um `return` mal colocado para vazá-lo.
"""

from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.persistence.models import (
    Conversa,
    ExecucaoRotina,
    Interacao,
    Rotina,
    Usuario,
)
from app.persistence.tabelas import (
    ConversaTabela,
    ExecucaoRotinaTabela,
    InteracaoTabela,
    RotinaTabela,
    UsuarioTabela,
)


class _RepositorioBase:
    """Guarda a sessão. Os repositórios não a criam nem a fecham."""

    def __init__(self, sessao: AsyncSession) -> None:
        self._sessao = sessao


class UsuarioRepository(_RepositorioBase):
    """Projeção local da identidade federada.

    Existe para que conversas, interações, rotinas e sessões tenham a que
    apontar. `garantir` é chamado no callback do login, que materializa a
    linha, e pela dependência que resolve a sessão (api/deps.py), a cada
    requisição autenticada, que mantém `visto_em` atualizado.
    """

    async def garantir(
        self,
        usuario_id: str,
        nome: str,
        perfil: str,
        email: str | None = None,
    ) -> None:
        """Registra ou atualiza a projeção do usuário. Idempotente.

        `visto_em` é reescrito a cada chamada: é o que distingue um
        usuário que existe de um usuário que usa. `criado_em` não é
        tocado no conflito, porque é o primeiro acesso e não o último.
        """
        agora = datetime.now(UTC)
        comando = pg_insert(UsuarioTabela).values(
            id=usuario_id,
            nome=nome,
            perfil=perfil,
            email=email,
            criado_em=agora,
            visto_em=agora,
        )
        await self._sessao.execute(
            comando.on_conflict_do_update(
                index_elements=[UsuarioTabela.id],
                set_={
                    "nome": comando.excluded.nome,
                    "perfil": comando.excluded.perfil,
                    "email": comando.excluded.email,
                    "visto_em": comando.excluded.visto_em,
                },
            )
        )

    async def obter(self, usuario_id: str) -> Usuario | None:
        """Recupera a projeção de um usuário, ou None."""
        linha = await self._sessao.get(UsuarioTabela, usuario_id)
        return linha.to_dominio() if linha else None


class ConversaRepository(_RepositorioBase):
    """Sessões de conversa e seu vínculo com o executor."""

    async def obter(self, conversa_id: str, usuario_id: str) -> Conversa | None:
        """Recupera uma conversa do usuário, ou None se não existir.

        Recebe `usuario_id` de propósito: um conversa_id só é válido para
        quem o criou. Sem esse filtro, adivinhar um id daria acesso ao
        histórico de outro usuário no Copilot.
        """
        resultado = await self._sessao.execute(
            select(ConversaTabela).where(
                ConversaTabela.id == conversa_id,
                ConversaTabela.usuario_id == usuario_id,
            )
        )
        linha = resultado.scalar_one_or_none()
        return linha.to_dominio() if linha else None

    async def criar(self, conversa: Conversa) -> None:
        """Registra uma nova conversa."""
        self._sessao.add(ConversaTabela.de_dominio(conversa))
        await self._sessao.flush()

    async def vincular_externa(self, conversa_id: str, conversa_externa_id: str) -> None:
        """Grava o conversationId do Direct Line obtido no primeiro turno."""
        await self._sessao.execute(
            update(ConversaTabela)
            .where(ConversaTabela.id == conversa_id)
            .values(
                conversa_externa_id=conversa_externa_id,
                atualizada_em=datetime.now(UTC),
            )
        )

    async def listar_por_usuario(
        self, usuario_id: str, *, incluir_arquivadas: bool = False
    ) -> list[Conversa]:
        """Conversas do usuário, mais recente primeiro, para a tela de histórico."""
        consulta = select(ConversaTabela).where(ConversaTabela.usuario_id == usuario_id)
        if not incluir_arquivadas:
            consulta = consulta.where(ConversaTabela.arquivada_em.is_(None))
        consulta = consulta.order_by(ConversaTabela.atualizada_em.desc())

        resultado = await self._sessao.execute(consulta)
        return [linha.to_dominio() for linha in resultado.scalars()]

    async def definir_titulo(self, conversa_id: str, titulo: str) -> None:
        """Grava o título derivado do primeiro turno da conversa."""
        await self._sessao.execute(
            update(ConversaTabela)
            .where(ConversaTabela.id == conversa_id)
            .values(titulo=titulo, atualizada_em=datetime.now(UTC))
        )

    async def arquivar(self, conversa_id: str, usuario_id: str) -> None:
        """Marca a conversa como arquivada, sem apagá-la.

        Arquivar e não excluir é decisão de rastreabilidade: o registro
        das interações precisa sobreviver à limpeza que o usuário faz na
        própria lista.

        O `usuario_id` no WHERE é o que impede arquivar a conversa de
        outra pessoa com um id adivinhado.
        """
        agora = datetime.now(UTC)
        await self._sessao.execute(
            update(ConversaTabela)
            .where(
                ConversaTabela.id == conversa_id,
                ConversaTabela.usuario_id == usuario_id,
            )
            .values(arquivada_em=agora, atualizada_em=agora)
        )


class InteracaoRepository(_RepositorioBase):
    """Registro das interações — base do histórico e da análise."""

    async def salvar(self, interacao: Interacao) -> None:
        """Persiste a interação.

        Chamado em todos os desfechos, bloqueios inclusive. Uma falha
        aqui deve propagar: responder sem registrar violaria a exigência
        de rastreabilidade.

        Também toca `conversa.atualizada_em`, porque é a interação que
        torna a conversa recente — sem isso a lista de histórico ficaria
        ordenada pela criação e uma conversa retomada afundaria.
        """
        self._sessao.add(InteracaoTabela.de_dominio(interacao))
        await self._sessao.execute(
            update(ConversaTabela)
            .where(ConversaTabela.id == interacao.conversa_id)
            .values(atualizada_em=interacao.criada_em)
        )
        await self._sessao.flush()

    async def listar_por_conversa(self, conversa_id: str, usuario_id: str) -> list[Interacao]:
        """Turnos de uma conversa, em ordem cronológica.

        Filtra por `usuario_id` pela mesma razão que `ConversaRepository.obter`.
        """
        resultado = await self._sessao.execute(
            select(InteracaoTabela)
            .where(
                InteracaoTabela.conversa_id == conversa_id,
                InteracaoTabela.usuario_id == usuario_id,
            )
            .order_by(InteracaoTabela.criada_em)
        )
        return [linha.to_dominio() for linha in resultado.scalars()]

    async def listar_por_usuario(self, usuario_id: str, *, limite: int = 50) -> list[Interacao]:
        """Interações recentes de um usuário.

        O limite é aplicado no SQL, e não depois: trazer tudo para cortar
        em Python transformaria um usuário antigo num problema de memória.
        """
        resultado = await self._sessao.execute(
            select(InteracaoTabela)
            .where(InteracaoTabela.usuario_id == usuario_id)
            .order_by(InteracaoTabela.criada_em.desc())
            .limit(limite)
        )
        return [linha.to_dominio() for linha in resultado.scalars()]


class RotinaRepository(_RepositorioBase):
    """Prompts agendados e sua configuração."""

    async def obter(self, rotina_id: str) -> Rotina | None:
        """Recupera uma rotina pelo id, sem filtrar por dono.

        Diferente de `ConversaRepository.obter`: quem chama aqui é o
        agendador, que não tem usuário na sessão. O controle de acesso da
        rota de gestão é aplicado em api/routes/rotinas.py, comparando
        `dono_id` com o usuário autenticado.
        """
        linha = await self._sessao.get(RotinaTabela, rotina_id)
        return linha.to_dominio() if linha else None

    async def listar_por_dono(self, dono_id: str) -> list[Rotina]:
        """Rotinas de um usuário, para a tela de gestão."""
        resultado = await self._sessao.execute(
            select(RotinaTabela)
            .where(RotinaTabela.dono_id == dono_id)
            .order_by(RotinaTabela.criada_em.desc())
        )
        return [linha.to_dominio() for linha in resultado.scalars()]

    async def listar_ativas(self) -> list[Rotina]:
        """Todas as rotinas ativas, para o agendador reconstruir a agenda."""
        resultado = await self._sessao.execute(
            select(RotinaTabela).where(RotinaTabela.ativa.is_(True))
        )
        return [linha.to_dominio() for linha in resultado.scalars()]

    async def criar(self, rotina: Rotina) -> None:
        self._sessao.add(RotinaTabela.de_dominio(rotina))
        await self._sessao.flush()

    async def atualizar(self, rotina: Rotina) -> None:
        await self._sessao.execute(
            update(RotinaTabela)
            .where(RotinaTabela.id == rotina.id)
            .values(
                nome=rotina.nome,
                prompt=rotina.prompt,
                agenda_cron=rotina.agenda_cron,
                timezone=rotina.timezone,
                ativa=rotina.ativa,
                intencao_prevista=rotina.intencao_prevista,
                atualizada_em=datetime.now(UTC),
            )
        )

    async def remover(self, rotina_id: str) -> None:
        """Apaga a rotina — apenas se ela nunca tiver disparado.

        Uma rotina com execuções registradas não é apagável: a chave
        estrangeira de `execucao_rotina` é `RESTRICT`, e é assim de
        propósito. Apagar levaria junto a trilha dos disparos, inclusive
        a dos que foram bloqueados — exatamente o registro que a
        exigência de rastreabilidade manda preservar.

        Para essas, a operação correta é desativar (`ativa = False`), que
        tira a rotina da agenda sem apagar o que ela já fez. O erro é
        levantado aqui, com a orientação, em vez de deixar o banco
        devolver uma violação de integridade que o chamador teria de
        interpretar.
        """
        tem_execucao = await self._sessao.execute(
            select(ExecucaoRotinaTabela.id)
            .where(ExecucaoRotinaTabela.rotina_id == rotina_id)
            .limit(1)
        )
        if tem_execucao.scalar_one_or_none() is not None:
            raise ValueError(
                f"A rotina {rotina_id} já disparou e não pode ser apagada sem "
                "levar junto o histórico de execuções. Desative-a "
                "(ativa=False) em vez de removê-la."
            )

        linha = await self._sessao.get(RotinaTabela, rotina_id)
        if linha is not None:
            await self._sessao.delete(linha)
            await self._sessao.flush()


class ExecucaoRepository(_RepositorioBase):
    """Histórico de disparos das rotinas."""

    async def registrar_inicio(self, execucao: ExecucaoRotina) -> None:
        """Grava a execução antes de rodar o pipeline.

        Registrar o início separado da conclusão é o que torna visível
        uma rotina que travou: sem isso, um disparo que nunca termina
        simplesmente não aparece em lugar nenhum.
        """
        self._sessao.add(ExecucaoRotinaTabela.de_dominio(execucao))
        await self._sessao.flush()

    async def registrar_fim(
        self,
        execucao_id: str,
        *,
        concluida_em: datetime,
        status: str,
        interacao_id: str | None = None,
        erro: str | None = None,
    ) -> None:
        """Fecha a execução com o resultado do pipeline."""
        await self._sessao.execute(
            update(ExecucaoRotinaTabela)
            .where(ExecucaoRotinaTabela.id == execucao_id)
            .values(
                concluida_em=concluida_em,
                status=status,
                interacao_id=interacao_id,
                erro=erro,
            )
        )

    async def listar_por_rotina(self, rotina_id: str, *, limite: int = 20) -> list[ExecucaoRotina]:
        """Disparos recentes de uma rotina, mais recente primeiro."""
        resultado = await self._sessao.execute(
            select(ExecucaoRotinaTabela)
            .where(ExecucaoRotinaTabela.rotina_id == rotina_id)
            .order_by(ExecucaoRotinaTabela.iniciada_em.desc())
            .limit(limite)
        )
        return [linha.to_dominio() for linha in resultado.scalars()]
