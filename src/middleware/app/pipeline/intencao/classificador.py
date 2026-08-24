"""Classificador de intenções.

Mapeia a mensagem (já sanitizada) para uma intenção do catálogo.
Candidatos a implementação (decisão de stack na Sprint 2): fine-tuning
de modelo pt-BR (ex.: BERTimbau) ou classificação zero-shot via LLM.
A interface abaixo é estável independente da escolha.

Regra de decisão: intenção fora do catálogo ou com confiança abaixo do
limiar é recusada pelo orquestrador antes de chegar ao Copilot.
"""

from dataclasses import dataclass


@dataclass
class ResultadoIntencao:
    """Intenção classificada para uma mensagem."""

    intencao_id: str | None  # None quando nenhuma intenção do catálogo se aplica
    confianca: float  # 0.0 a 1.0


async def classificar(texto: str) -> ResultadoIntencao:
    """Classifica o texto contra o catálogo de intenções."""
    raise NotImplementedError("Modelo de classificação a definir na Sprint 2")
