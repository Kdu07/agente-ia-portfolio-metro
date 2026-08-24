"""Gravação e consulta dos registros do middleware.

Interface de persistência usada pelo orquestrador, pelas rotas e pelo
agendador. A implementação concreta (SQLAlchemy 2 async sobre
PostgreSQL, conforme infra/docker-compose.yml) será definida na onda 1.

Divisão dos repositórios por agregado, e não por tabela: `InteracaoRepository`
concentra tudo o que se lê e escreve sobre interações, incluindo o
histórico; as agregações do dashboard ficam em `analytics/consultas.py`,
porque as perguntas da análise mudam com muito mais frequência que o
esquema e não devem arrastar este módulo junto.
"""

from datetime import datetime

from app.persistence.models import Conversa, ExecucaoRotina, Interacao, Rotina


class ConversaRepository:
    """Sessões de conversa e seu vínculo com o executor."""

    async def obter(self, conversa_id: str, usuario_id: str) -> Conversa | None:
        """Recupera uma conversa do usuário, ou None se não existir.

        Recebe `usuario_id` de propósito: um conversa_id só é válido para
        quem o criou. Sem esse filtro, adivinhar um id daria acesso ao
        histórico de outro usuário no Copilot.
        """
        raise NotImplementedError("Persistência a implementar na onda 1")

    async def criar(self, conversa: Conversa) -> None:
        """Registra uma nova conversa."""
        raise NotImplementedError("Persistência a implementar na onda 1")

    async def vincular_externa(self, conversa_id: str, conversa_externa_id: str) -> None:
        """Grava o conversationId do Direct Line obtido no primeiro turno."""
        raise NotImplementedError("Persistência a implementar na onda 1")

    async def listar_por_usuario(
        self, usuario_id: str, *, incluir_arquivadas: bool = False
    ) -> list[Conversa]:
        """Conversas do usuário, mais recente primeiro, para a tela de histórico."""
        raise NotImplementedError("Persistência a implementar na onda 1")

    async def definir_titulo(self, conversa_id: str, titulo: str) -> None:
        """Grava o título derivado do primeiro turno da conversa."""
        raise NotImplementedError("Persistência a implementar na onda 1")

    async def arquivar(self, conversa_id: str, usuario_id: str) -> None:
        """Marca a conversa como arquivada, sem apagá-la.

        Arquivar e não excluir é decisão de rastreabilidade: o registro
        das interações precisa sobreviver à limpeza que o usuário faz na
        própria lista.
        """
        raise NotImplementedError("Persistência a implementar na onda 1")


class InteracaoRepository:
    """Registro das interações — base do histórico e da análise."""

    async def salvar(self, interacao: Interacao) -> None:
        """Persiste a interação.

        Chamado em todos os desfechos, bloqueios inclusive. Uma falha
        aqui deve propagar: responder sem registrar violaria a exigência
        de rastreabilidade.
        """
        raise NotImplementedError("Persistência a implementar na onda 1")

    async def listar_por_conversa(self, conversa_id: str, usuario_id: str) -> list[Interacao]:
        """Turnos de uma conversa, em ordem cronológica.

        Filtra por `usuario_id` pela mesma razão que `ConversaRepository.obter`.
        """
        raise NotImplementedError("Persistência a implementar na onda 1")

    async def listar_por_usuario(
        self, usuario_id: str, *, limite: int = 50
    ) -> list[Interacao]:
        """Interações recentes de um usuário."""
        raise NotImplementedError("Persistência a implementar na onda 1")


class RotinaRepository:
    """Prompts agendados e sua configuração."""

    async def obter(self, rotina_id: str) -> Rotina | None:
        """Recupera uma rotina pelo id, sem filtrar por dono.

        Diferente de `ConversaRepository.obter`: quem chama aqui é o
        agendador, que não tem usuário na sessão. O controle de acesso da
        rota de gestão é aplicado em api/routes/rotinas.py, comparando
        `dono_id` com o usuário autenticado.
        """
        raise NotImplementedError("Persistência a implementar na onda 5")

    async def listar_por_dono(self, dono_id: str) -> list[Rotina]:
        """Rotinas de um usuário, para a tela de gestão."""
        raise NotImplementedError("Persistência a implementar na onda 5")

    async def listar_ativas(self) -> list[Rotina]:
        """Todas as rotinas ativas, para o agendador reconstruir a agenda."""
        raise NotImplementedError("Persistência a implementar na onda 5")

    async def criar(self, rotina: Rotina) -> None:
        raise NotImplementedError("Persistência a implementar na onda 5")

    async def atualizar(self, rotina: Rotina) -> None:
        raise NotImplementedError("Persistência a implementar na onda 5")

    async def remover(self, rotina_id: str) -> None:
        raise NotImplementedError("Persistência a implementar na onda 5")


class ExecucaoRepository:
    """Histórico de disparos das rotinas."""

    async def registrar_inicio(self, execucao: ExecucaoRotina) -> None:
        """Grava a execução antes de rodar o pipeline.

        Registrar o início separado da conclusão é o que torna visível
        uma rotina que travou: sem isso, um disparo que nunca termina
        simplesmente não aparece em lugar nenhum.
        """
        raise NotImplementedError("Persistência a implementar na onda 5")

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
        raise NotImplementedError("Persistência a implementar na onda 5")

    async def listar_por_rotina(
        self, rotina_id: str, *, limite: int = 20
    ) -> list[ExecucaoRotina]:
        """Disparos recentes de uma rotina, mais recente primeiro."""
        raise NotImplementedError("Persistência a implementar na onda 5")
