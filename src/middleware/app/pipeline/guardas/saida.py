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

Duas camadas, espelhando `injecao/`:

1. regras determinísticas — marcadores de instrução, pedido de
   credencial e URL para domínio fora de `settings.saida_dominios_permitidos`;
2. Prompt Shields do Azure AI Content Safety no modo de detecção de
   ataque indireto (`documents`), que é exatamente o caso de uso.

Falha do serviço com credencial configurada falha FECHADO, como na
guarda de injeção: entregar uma resposta possivelmente envenenada é pior
que pedir ao usuário que tente de novo. Credencial AUSENTE é outra
coisa — decisão de implantação, não queda — e deixa valendo só as
regras, com aviso no log (decisão de 15/09).
"""

import logging
import re
from collections.abc import Iterator
from dataclasses import dataclass
from urllib.parse import urlsplit

import httpx

from app.config import settings
from app.pipeline.guardas import content_safety
from app.pipeline.guardas.injecao.regras import PADROES_SUSPEITOS

logger = logging.getLogger(__name__)

# Montagem da chamada, tempo limite e fatiamento são os mesmos das guardas
# de entrada e vivem em content_safety.py. Resposta maior que o teto vai em
# várias chamadas, e basta uma detectar ataque para reter.
API_VERSION = content_safety.API_VERSION
LIMITE_CARACTERES = content_safety.LIMITE_CARACTERES

# Padrões iniciais; expandir conforme testes adversariais da equipe. Os da
# entrada (`PADROES_SUSPEITOS`) valem aqui também — a instrução embutida
# num documento costuma usar o mesmo vocabulário do ataque direto.
PADROES_INSTRUCAO: list[re.Pattern] = [
    re.compile(r"ignore\s+(todas\s+)?(as\s+)?(regras|instru[cç][oõ]es)", re.IGNORECASE),
    # Ancorado em início de linha, e sem `agente`: o vetor é um documento
    # fingindo turno de diálogo, não a palavra solta. Sem a âncora,
    # "Agente: João Silva" numa ficha de fiscalização retinha resposta
    # legítima — e `agente` como alvo de instrução segue coberto abaixo.
    re.compile(r"^\s*(assistente|sistema|system)\s*:", re.IGNORECASE | re.MULTILINE),
    re.compile(
        r"\b(aten[cç][aã]o|nota|instru[cç][aã]o)\s*,?\s*(ao\s+|para\s+o\s+)?"
        r"(assistente|agente|modelo|ia)\b",
        re.IGNORECASE,
    ),
    re.compile(r"n[aã]o\s+(mencione|informe|diga|revele)\s+(que|ao\s+usu[aá]rio)", re.IGNORECASE),
    re.compile(r"system\s+prompt|prompt\s+de\s+sistema", re.IGNORECASE),
]

PADROES_CREDENCIAL: list[re.Pattern] = [
    re.compile(
        r"\b(informe|digite|envie|confirme|forne[cç]a)\s+(sua|seu|a|o)\s+"
        r"(senha|credenciais?|token|c[oó]digo\s+de\s+verifica[cç][aã]o|mfa)\b",
        re.IGNORECASE,
    ),
]

# Parênteses e colchetes fora da URL: é o que separa o endereço da sintaxe
# de link em markdown, que o Gemini usa.
_URL = re.compile(r"(?:https?://|www\.)[^\s<>()\[\]\"']+", re.IGNORECASE)
_MAILTO = re.compile(r"mailto:([^\s<>()\[\]\"']+)", re.IGNORECASE)

# Encaminhamento para caixa postal. O verbo sozinho não acusa: pedir que
# se encaminhe algo para `contratos@metro.sp.gov.br` é orientação
# legítima, e o que distingue exfiltração é o destino. Por isso o domínio
# é capturado e passa pela mesma allowlist das URLs.
_ENCAMINHAMENTO = re.compile(
    r"\b(?:envie|encaminhe|mande|repasse)\s+.{0,40}?para\s+[\w.+-]+@([\w-]+\.[\w.]+)",
    re.IGNORECASE,
)


@dataclass
class ResultadoSaida:
    """Veredito sobre a resposta produzida pelo executor."""

    suspeita: bool
    confianca: float  # 0.0 a 1.0
    motivo: str  # para o registro e o alerta; nunca devolvido ao usuário


async def verificar(
    texto: str,
    intencao_id: str,
    *,
    transporte: httpx.AsyncBaseTransport | None = None,
) -> ResultadoSaida:
    """Avalia a resposta do executor antes da entrega ao usuário.

    Recebe `intencao_id` de propósito: a coerência entre o que foi
    perguntado e o que voltou é o sinal mais forte disponível aqui. Nesta
    versão, pedido de credencial e URL externa são suspeitos em qualquer
    intenção — o catálogo não diz qual intenção pode devolver link —, e a
    intenção entra no motivo (`url_fora_allowlist@consultar_avanco`) para
    o registro mostrar em que pergunta o problema apareceu.

    O texto verificado é a resposta inteira, bloco `Fontes:` incluso,
    porque é isso que chega ao usuário. `transporte` existe para os
    testes dublarem o Content Safety sem rede.
    """
    motivo = _avaliar_regras(texto)
    if motivo is not None:
        return ResultadoSaida(suspeita=True, confianca=1.0, motivo=f"{motivo}@{intencao_id}")

    if not content_safety.configurado():
        logger.warning("Guarda de saída sem Content Safety configurado; só as regras valem")
        return ResultadoSaida(suspeita=False, confianca=0.0, motivo="limpo_so_regras")

    resultado = await _prompt_shields(texto, transporte)
    if resultado.suspeita:
        resultado.motivo = f"{resultado.motivo}@{intencao_id}"
    return resultado


def _avaliar_regras(texto: str) -> str | None:
    """Primeira camada: devolve o motivo da suspeita, ou `None`."""
    if any(padrao.search(texto) for padrao in [*PADROES_SUSPEITOS, *PADROES_INSTRUCAO]):
        return "instrucao_embutida"
    if any(padrao.search(texto) for padrao in PADROES_CREDENCIAL):
        return "pedido_credencial"
    if any(not _dominio_permitido(host) for host in _hosts_citados(texto)):
        return "url_fora_allowlist"
    return None


def _hosts_citados(texto: str) -> Iterator[str]:
    """Hosts das URLs, dos `mailto:` e dos encaminhamentos por e-mail."""
    for url in _URL.findall(texto):
        url = url.rstrip(".,;:!?")
        if not url.lower().startswith("http"):
            url = f"http://{url}"
        yield (urlsplit(url).hostname or "").lower()
    for endereco in _MAILTO.findall(texto):
        yield endereco.rsplit("@", 1)[-1].split("?", 1)[0].rstrip(".,;:!?").lower()
    for dominio in _ENCAMINHAMENTO.findall(texto):
        yield dominio.rstrip(".,;:!?").lower()


def _dominio_permitido(host: str) -> bool:
    """Casa por sufixo de rótulo: `x.sharepoint.com` sim, `evilsharepoint.com` não."""
    return any(
        host == dominio or host.endswith(f".{dominio}")
        for dominio in (d.lower() for d in settings.saida_dominios_permitidos)
    )


async def _prompt_shields(
    texto: str, transporte: httpx.AsyncBaseTransport | None
) -> ResultadoSaida:
    """Segunda camada: o texto vai como documento, que é o caso de ataque indireto."""
    async with content_safety.sessao(transporte) as servico:
        for parte in content_safety.partes(texto):
            try:
                dados = await servico.analisar(
                    "text:shieldPrompt", {"userPrompt": "", "documents": [parte]}
                )
            except content_safety.Indisponivel as erro:
                return _indisponivel(erro.detalhe)

            analises = _analises_de(dados)
            if analises is None:
                return _indisponivel("documentsAnalysis invalida para o documento enviado")
            if any(analise.get("attackDetected") is True for analise in analises):
                return ResultadoSaida(
                    suspeita=True, confianca=0.9, motivo="prompt_shields_documento"
                )

    return ResultadoSaida(suspeita=False, confianca=0.0, motivo="limpo")


def _analises_de(dados: dict) -> list[dict] | None:
    """Cada chamada envia um documento e exige um veredito booleano."""
    analises = dados.get("documentsAnalysis")
    if not isinstance(analises, list) or len(analises) != 1:
        return None
    if not all(isinstance(a, dict) and isinstance(a.get("attackDetected"), bool) for a in analises):
        return None
    return analises


def _indisponivel(detalhe: str) -> ResultadoSaida:
    """Falha fechado: na dúvida, a resposta não é entregue."""
    logger.warning("Content Safety indisponível na guarda de saída (%s)", detalhe)
    return ResultadoSaida(suspeita=True, confianca=1.0, motivo="servico_indisponivel")
