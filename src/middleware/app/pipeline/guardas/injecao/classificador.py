"""Classificador de prompt injection.

Segunda barreira, para os ataques que as regras (regras.py) não pegam:
avaliação por modelo. A implementação é o **Prompt Shields** do Azure AI
Content Safety — a mesma API que a guarda de abuso usa para as
categorias de conteúdo, e a mesma que a guarda de saída usa no modo de
ataque indireto. Aqui o texto vai em `userPrompt`, que é o modo de
ataque direto: quem escreveu a mensagem é o suspeito.

A interface é estável independente da escolha: se o Prompt Shields for
trocado por um modelo dedicado ou por um LLM juiz, só este módulo muda.

Nota de segurança: uma falha ao chamar o serviço NÃO vira "mensagem
liberada". Com credencial configurada, a decisão é falhar FECHADO —
deixar passar por queda de infraestrutura transformaria uma
indisponibilidade do Content Safety em janela de ataque. Credencial
AUSENTE é outra coisa, e não uma queda: é decisão de implantação, e
deixa valendo só as regras determinísticas que o orquestrador já
aplicou antes desta chamada, com aviso no log — a mesma decisão tomada
em 15/09 para a guarda de saída.
"""

import logging
from dataclasses import dataclass

import httpx

from app.pipeline.guardas import content_safety

logger = logging.getLogger(__name__)


@dataclass
class ResultadoInjection:
    """Veredito do classificador sobre uma mensagem."""

    suspeita: bool
    confianca: float  # 0.0 a 1.0
    motivo: str  # descrição curta para o registro; nunca devolvida ao usuário
    # True quando a suspeita vem da falta do serviço, e não de detecção. A
    # mensagem continua barrada; muda só o desfecho registrado.
    indisponivel: bool = False


async def classificar(
    texto: str, *, transporte: httpx.AsyncBaseTransport | None = None
) -> ResultadoInjection:
    """Avalia se o texto é uma tentativa de prompt injection.

    O Prompt Shields devolve um booleano, e não um score: a confiança de
    uma detecção é fixa (0.9) e existe para o registro, não para um
    limiar. `transporte` existe para os testes dublarem o Content Safety
    sem rede.
    """
    if not texto.strip():
        # Mensagem vazia não ataca ninguém, e o serviço rejeitaria o
        # corpo — o que, falhando fechado, viraria um bloqueio absurdo.
        # O orquestrador já trata a vazia como fora de escopo na etapa 3.
        return ResultadoInjection(suspeita=False, confianca=0.0, motivo="vazio")

    if not content_safety.configurado():
        logger.warning("Guarda de injeção sem Content Safety configurado; só as regras valem")
        return ResultadoInjection(suspeita=False, confianca=0.0, motivo="limpo_so_regras")

    async with content_safety.sessao(transporte) as servico:
        # Mensagem acima do teto por chamada vai em partes; basta uma
        # detectar ataque para bloquear. `ChatRequest` limita a 4000
        # caracteres, mas o pipeline também atende rotinas.
        for parte in content_safety.partes(texto):
            try:
                dados = await servico.analisar(
                    "text:shieldPrompt", {"userPrompt": parte, "documents": []}
                )
            except content_safety.Indisponivel as erro:
                return _indisponivel(erro.detalhe)

            analise = dados.get("userPromptAnalysis")
            if not isinstance(analise, dict):
                return _indisponivel("resposta sem userPromptAnalysis")
            ataque = analise.get("attackDetected")
            if not isinstance(ataque, bool):
                return _indisponivel("userPromptAnalysis sem attackDetected booleano")
            if ataque:
                return ResultadoInjection(
                    suspeita=True, confianca=0.9, motivo="prompt_shields_usuario"
                )

    return ResultadoInjection(suspeita=False, confianca=0.0, motivo="limpo")


def _indisponivel(detalhe: str) -> ResultadoInjection:
    """Falha fechado: na dúvida, o executor não é acionado."""
    logger.warning("Content Safety indisponível na guarda de injeção (%s)", detalhe)
    return ResultadoInjection(
        suspeita=True, confianca=1.0, motivo="servico_indisponivel", indisponivel=True
    )
