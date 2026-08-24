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
    conversa_externa_id: str  # conversationId do Direct Line, para os próximos turnos
    dados: dict | None = None  # anexos estruturados (cards, tabelas), se houver


class CopilotClient:
    """Encapsula a conversa com o Copilot Studio via Direct Line."""

    async def enviar(
        self,
        texto_mascarado: str,
        intencao_id: str,
        exige_confirmacao: bool,
        conversa_externa_id: str | None = None,
    ) -> RespostaCopilot:
        """Envia a mensagem sanitizada e aguarda a resposta do Copilot.

        `intencao_id` e `exige_confirmacao` viajam como METADADOS da
        activity, nunca concatenados ao texto: a entrada do usuário é
        sempre dado rotulado, jamais instrução (ver copilot/topicos.md).
        `exige_confirmacao` sinaliza ao tópico que a ação altera dado e
        precisa de confirmação prévia do usuário.

        `conversa_externa_id` é o conversationId do Direct Line, e não o
        conversa_id do middleware — a tradução entre os dois é feita pelo
        orquestrador, para que este módulo continue sendo o único a
        conhecer o Copilot.

        TODO (sprint técnica): implementar com httpx contra a API Direct
        Line (iniciar conversa, postar activity, poll/stream de resposta),
        usando settings.directline_endpoint, settings.directline_secret e
        settings.copilot_timeout_seconds.
        """
        raise NotImplementedError("Integração Direct Line pendente")
