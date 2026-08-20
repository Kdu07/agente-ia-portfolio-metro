"""Cliente do Copilot Studio via canal Direct Line (Bot Framework).

Único ponto do middleware que conhece o Copilot: envia o prompt já
sanitizado (mascarado e com a intenção resolvida) e devolve a resposta.
Se o executor mudar no futuro (outro agente, outra plataforma), apenas
este módulo é substituído.

Contrato com o Copilot: a entrada do usuário é enviada sempre como DADO
rotulado (activity com metadados de intenção), nunca concatenada a
instruções — parte da defesa contra prompt injection.
"""

from dataclasses import dataclass


@dataclass
class RespostaCopilot:
    """Resposta devolvida pelo Copilot Studio."""

    texto: str
    dados: dict | None = None  # anexos estruturados (cards, tabelas), se houver


class CopilotClient:
    """Encapsula a conversa com o Copilot Studio via Direct Line."""

    async def enviar(
        self, texto_mascarado: str, intencao_id: str, conversa_id: str | None = None
    ) -> RespostaCopilot:
        """Envia a mensagem sanitizada e aguarda a resposta do Copilot.

        TODO (sprint técnica): implementar com httpx contra a API Direct
        Line (iniciar conversa, postar activity, poll/stream de resposta),
        usando settings.directline_endpoint e settings.directline_secret.
        """
        raise NotImplementedError("Integração Direct Line pendente")
