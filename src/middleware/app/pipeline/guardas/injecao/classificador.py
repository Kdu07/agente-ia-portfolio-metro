"""Classificador de prompt injection.

Segunda barreira, para os ataques que as regras (regras.py) não pegam:
avaliação por modelo. A implementação prevista é o **Prompt Shields** do
Azure AI Content Safety, que roda no tenant homologado do parceiro e
cobre tanto jailbreak quanto ataque indireto — a mesma API que a guarda
de abuso usa para as categorias de conteúdo.

A interface abaixo é estável independente da escolha: se o Prompt
Shields for trocado por um modelo dedicado ou por um LLM juiz, só este
módulo muda.

Nota de segurança: uma falha de rede ao chamar o serviço NÃO pode virar
"mensagem liberada". A decisão de projeto é falhar fechado — ver o TODO
de `classificar`.
"""

from dataclasses import dataclass


@dataclass
class ResultadoInjection:
    """Veredito do classificador sobre uma mensagem."""

    suspeita: bool
    confianca: float  # 0.0 a 1.0
    motivo: str  # descrição curta para o registro; nunca devolvida ao usuário


async def classificar(texto: str) -> ResultadoInjection:
    """Avalia se o texto é uma tentativa de prompt injection.

    TODO (onda 2): implementar com httpx contra o endpoint de Prompt
    Shields do Azure AI Content Safety, usando
    settings.content_safety_endpoint e settings.content_safety_key.

    Em caso de indisponibilidade do serviço, devolver
    `suspeita=True, motivo="servico_indisponivel"`: na dúvida, não se
    aciona o executor. Deixar passar por falha de infraestrutura
    transformaria uma queda do Content Safety em janela de ataque.
    """
    raise NotImplementedError("Integração com Azure AI Content Safety pendente (onda 2)")
