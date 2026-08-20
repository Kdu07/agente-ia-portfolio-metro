"""Gravação e consulta dos registros de interação.

Interface de persistência usada pelo orquestrador. A implementação
concreta (SQLAlchemy/PostgreSQL, conforme docker-compose de infra/)
será definida na Sprint 2.
"""

from app.persistence.models import Interacao, MapeamentoPII


class InteracaoRepository:
    """Acesso ao histórico de interações (auditoria e analytics)."""

    async def salvar(
        self, interacao: Interacao, mapeamentos: list[MapeamentoPII]
    ) -> None:
        """Persiste a interação mascarada e seus mapeamentos de PII."""
        raise NotImplementedError("Persistência a implementar na Sprint 2")

    async def listar_por_usuario(self, usuario_id: str) -> list[Interacao]:
        """Consulta o histórico de um usuário (sem os valores de PII)."""
        raise NotImplementedError("Persistência a implementar na Sprint 2")
