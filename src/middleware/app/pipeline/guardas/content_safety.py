"""Cliente do Azure AI Content Safety, compartilhado pelas três guardas.

Uma única dependência externa cobre as três avaliações, em dois
endpoints: `text:shieldPrompt` (Prompt Shields) para injeção direta, na
entrada, e indireta, na resposta; `text:analyze` para as categorias de
conteúdo da guarda de abuso.

O que este módulo faz é o que as três têm em comum — montar a URL, o
cabeçalho de autenticação e o corpo, e transformar qualquer falha de
transporte, código de erro ou corpo ilegível em `Indisponivel`. O que
ele deliberadamente NÃO faz é decidir o que significa a
indisponibilidade: a guarda de injeção falha fechado e a de abuso falha
aberto, e essa divergência é a razão de a exceção subir em vez de virar
um veredito aqui dentro.

O recurso fica no tenant da equipe (g02), e não no do parceiro: é a
exposição declarada como risco R12 — o texto do prompt e o da resposta
saem do perímetro homologado por desenho. Isolar o acesso neste módulo é
o que torna um eventual reprovisionamento no tenant do parceiro uma
mudança de configuração, e não de código.
"""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

API_VERSION = "2024-09-01"
# Curto de propósito: nas guardas de entrada o usuário ainda espera o
# início do processamento, e na de saída a resposta já está pronta. Sem
# nova tentativa pelo mesmo motivo — o tempo esgotado já é um veredito.
TIMEOUT_SEGUNDOS = 10.0
# Teto de caracteres por chamada, imposto pelo serviço. Texto maior vai
# em várias chamadas; o que fazer com cada veredito é de quem chama.
LIMITE_CARACTERES = 10_000


class Indisponivel(Exception):
    """O serviço não produziu veredito.

    Cobre queda de rede, tempo esgotado, código de erro e corpo que não
    casa com o contrato. Quem captura decide o desfecho: reter (injeção e
    saída) ou seguir em frente registrando a degradação (abuso).
    """

    def __init__(self, detalhe: str) -> None:
        super().__init__(detalhe)
        self.detalhe = detalhe


def configurado() -> bool:
    """True quando há endpoint e chave para chamar o serviço.

    Credencial ausente é decisão de implantação, não queda — por isso é
    uma pergunta separada de `Indisponivel`, e cada guarda a responde
    valendo-se apenas das suas camadas locais (decisão de 15/09).
    """
    return bool(settings.content_safety_endpoint and settings.content_safety_key)


def partes(texto: str) -> list[str]:
    """Divide o texto no teto de caracteres aceito por chamada.

    Texto vazio produz uma parte vazia, e não lista vazia: quem chama
    decide se pula a avaliação, mas não deve fazê-lo por acidente de
    fatiamento.
    """
    return [
        texto[inicio : inicio + LIMITE_CARACTERES]
        for inicio in range(0, max(len(texto), 1), LIMITE_CARACTERES)
    ]


@dataclass
class Sessao:
    """Uma conexão aberta com o serviço, para uma ou várias chamadas."""

    _cliente: httpx.AsyncClient

    async def analisar(self, operacao: str, corpo: dict) -> dict:
        """Chama uma operação do Content Safety e devolve o corpo JSON.

        `operacao` é o segmento final da rota (`text:shieldPrompt`,
        `text:analyze`). Levanta `Indisponivel` em qualquer caminho que
        não termine num veredito legível.
        """
        url = f"{settings.content_safety_endpoint.rstrip('/')}/contentsafety/{operacao}"
        cabecalhos = {"Ocp-Apim-Subscription-Key": settings.content_safety_key}
        try:
            resposta = await self._cliente.post(
                url,
                params={"api-version": API_VERSION},
                json=corpo,
                headers=cabecalhos,
            )
        except httpx.TimeoutException:
            raise Indisponivel(f"tempo esgotado ({TIMEOUT_SEGUNDOS:.0f}s)") from None
        except httpx.TransportError as erro:
            raise Indisponivel(f"falha de rede ({type(erro).__name__})") from None

        if resposta.is_error:
            # Sem o corpo do erro: ele pode ecoar o texto enviado.
            raise Indisponivel(f"código {resposta.status_code}")

        try:
            dados = resposta.json()
        except ValueError:
            raise Indisponivel("resposta não é JSON") from None
        if not isinstance(dados, dict):
            raise Indisponivel("resposta não é um objeto") from None
        return dados


@asynccontextmanager
async def sessao(transporte: httpx.AsyncBaseTransport | None = None) -> AsyncIterator[Sessao]:
    """Abre uma sessão HTTP para as chamadas de uma avaliação.

    `transporte` existe para os testes dublarem o serviço sem rede, e é o
    mesmo parâmetro que as três guardas expõem.
    """
    async with httpx.AsyncClient(timeout=TIMEOUT_SEGUNDOS, transport=transporte) as cliente:
        yield Sessao(cliente)
