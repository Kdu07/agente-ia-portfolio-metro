"""Classificador de conteúdo abusivo.

Avalia a mensagem contra as categorias genéricas de moderação do Azure
AI Content Safety (ódio, sexual, violência, automutilação) e combina o
resultado com as políticas corporativas de `politicas.py`.

É a mesma API usada pela guarda de injeção, endpoint diferente: lá,
Prompt Shields; aqui, análise de texto por categoria. Uma única
dependência externa cobre as duas features de proteção, o que reduz o
número de recursos a provisionar no tenant do parceiro.
"""

from dataclasses import dataclass, field

from app.pipeline.guardas.abuso.politicas import ViolacaoPolitica


@dataclass
class ResultadoAbuso:
    """Veredito da guarda de abuso sobre uma mensagem."""

    abusiva: bool
    confianca: float  # 0.0 a 1.0
    # Categoria do Content Safety que disparou (ex.: "Hate", "Violence"),
    # quando o bloqueio veio da moderação genérica.
    categoria: str | None = None
    # Políticas corporativas violadas, quando o bloqueio veio de
    # politicas.py. As duas origens podem coexistir.
    violacoes: list[ViolacaoPolitica] = field(default_factory=list)

    @property
    def motivo(self) -> str:
        """Descrição curta para o registro; nunca devolvida ao usuário."""
        partes = [self.categoria] if self.categoria else []
        partes += [v.politica.value for v in self.violacoes]
        return ",".join(partes) or "nao_especificado"


async def classificar(texto: str) -> ResultadoAbuso:
    """Avalia se o texto configura uso indevido do agente.

    TODO (onda 2): implementar com httpx contra o endpoint de análise de
    texto do Azure AI Content Safety, usando settings.content_safety_endpoint,
    settings.content_safety_key e settings.content_safety_limiar_severidade;
    depois somar o resultado de `politicas.avaliar`.

    Ao contrário da guarda de injeção, aqui a decisão em caso de
    indisponibilidade do serviço é falhar ABERTO: bloquear todo o tráfego
    legítimo porque o moderador caiu seria pior que deixar passar um
    pedido malicioso ocasional, e a mensagem ainda passou pela guarda de
    injeção antes de chegar aqui. Registrar o desfecho degradado.
    """
    raise NotImplementedError("Integração com Azure AI Content Safety pendente (onda 2)")
