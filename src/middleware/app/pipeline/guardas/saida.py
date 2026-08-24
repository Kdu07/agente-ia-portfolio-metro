"""Guarda da resposta do executor — defesa contra injeção indireta.

Com o Copilot Studio lendo documentos do SharePoint, o ataque mais
plausível não chega pelo campo de texto: chega DENTRO de um documento.
Alguém deposita na biblioteca um arquivo com instruções embutidas, o
Copilot o recupera para compor a resposta, e a instrução volta ao
usuário como se fosse conteúdo legítimo.

Verificar apenas a entrada não cobre esse vetor, porque a entrada é
inocente — quem digitou "qual o status do projeto X?" não fez nada de
errado. Esta é a única barreira posicionada para enxergar o problema.

O que se procura na resposta é diferente do que se procura na entrada:

- instruções dirigidas ao agente, e não ao usuário ("ignore", "envie
  para", "não mencione que");
- solicitação de credencial, link de exfiltração ou ação fora do
  catálogo de intenções;
- conteúdo que contradiz a intenção classificada da pergunta.

Este último é o sinal mais específico e o mais barato: se o usuário
perguntou o status de um projeto e a resposta pede que ele acesse uma
URL externa, algo entrou no caminho — e não foi por ele.
"""

from dataclasses import dataclass


@dataclass
class ResultadoSaida:
    """Veredito sobre a resposta produzida pelo executor."""

    suspeita: bool
    confianca: float  # 0.0 a 1.0
    motivo: str  # para o registro e o alerta; nunca devolvido ao usuário


async def verificar(texto: str, intencao_id: str) -> ResultadoSaida:
    """Avalia a resposta do Copilot antes da entrega ao usuário.

    Recebe `intencao_id` de propósito: a coerência entre o que foi
    perguntado e o que voltou é o sinal mais forte disponível aqui, e
    sem a intenção não há como avaliá-la.

    TODO (onda 2): implementar em duas camadas, espelhando `injecao/`:
      1. regras determinísticas sobre a resposta — URLs para domínios
         fora da allowlist do parceiro, pedidos de credencial, marcadores
         de instrução;
      2. Prompt Shields do Azure AI Content Safety no modo de detecção de
         ataque indireto (`documents`), que é exatamente o caso de uso.

    Em caso de indisponibilidade, falhar FECHADO como na guarda de
    injeção: entregar uma resposta possivelmente envenenada é pior que
    pedir ao usuário que tente de novo.
    """
    raise NotImplementedError("Verificação de saída pendente (onda 2)")
