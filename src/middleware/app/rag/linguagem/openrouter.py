"""Adaptador do modelo de geração — OpenRouter, pela API no formato da OpenAI.

Alternativa ao `gemini.py` com o mesmo papel. O OpenRouter é um
roteador de provedores, e o modelo padrão é o mesmo Gemini Flash; o que
muda é a conta que paga e o caminho. A pergunta e os trechos passam pelo
OpenRouter antes de chegar ao provedor — mais um intermediário no
perímetro da seção 4.5, aceitável enquanto o dado for sintético.

Valem as mesmas três escolhas do `gemini.py`: instrução como mensagem
`system` e conteúdo como mensagem `user`, nunca concatenados; novas
tentativas só para o transitório; temperatura no padrão do provedor.

Sem SDK: é um POST com httpx, que o middleware já usa. O transporte é
injetável para os testes dublarem a rede sem chave nem crédito.
"""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any

import httpx

from app.config import settings
from app.rag.linguagem.base import ErroGeracao
from app.rag.linguagem.gemini import CODIGOS_TRANSITORIOS, ESPERA_INICIAL, TENTATIVAS

logger = logging.getLogger(__name__)

URL = "https://openrouter.ai/api/v1/chat/completions"


class ModeloOpenRouter:
    """Implementa `ModeloLinguagem` sobre a API do OpenRouter."""

    def __init__(
        self,
        chave: str,
        modelo: str,
        *,
        timeout: float,
        transporte: httpx.AsyncBaseTransport | None = None,
        tentativas: int = TENTATIVAS,
        espera_inicial: float = ESPERA_INICIAL,
        dormir: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        """`transporte` e `dormir` existem para os testes não usarem rede nem esperarem."""
        self._chave = chave
        self._modelo = modelo
        self._timeout = timeout
        self._transporte = transporte
        self._tentativas = max(1, tentativas)
        self._espera_inicial = espera_inicial
        self._dormir = dormir

    @classmethod
    def de_configuracao(cls) -> "ModeloOpenRouter":
        """Monta o adaptador a partir do `.env`, conferindo a chave antes de qualquer chamada."""
        if not settings.openrouter_api_key:
            raise RuntimeError("openrouter_api_key é obrigatória com llm_backend=openrouter")
        return cls(
            settings.openrouter_api_key,
            settings.openrouter_modelo,
            timeout=settings.openrouter_timeout_seconds,
        )

    @property
    def nome(self) -> str:
        return f"openrouter/{self._modelo}"

    async def gerar(self, *, instrucoes: str, conteudo: str) -> str:
        """Chama o modelo, repetindo as falhas transitórias com espera crescente.

        Um cliente por chamada, e não por processo: a fábrica monta o
        adaptador a cada requisição, e um cliente guardado nele ficaria
        aberto sem ninguém para fechá-lo.
        """
        corpo = {
            "model": self._modelo,
            "messages": [
                {"role": "system", "content": instrucoes},
                {"role": "user", "content": conteudo},
            ],
        }
        cabecalhos = {"Authorization": f"Bearer {self._chave}"}

        espera = self._espera_inicial
        async with httpx.AsyncClient(timeout=self._timeout, transport=self._transporte) as cliente:
            for tentativa in range(1, self._tentativas + 1):
                try:
                    resposta = await cliente.post(URL, json=corpo, headers=cabecalhos)
                except httpx.TimeoutException:
                    motivo = f"tempo esgotado ({self._timeout:.0f}s)"
                except httpx.TransportError as erro:
                    motivo = f"falha de rede ({type(erro).__name__})"
                else:
                    dados = _json_de(resposta)
                    codigo = _codigo_de_erro(resposta, dados)
                    if codigo is None:
                        return _texto_de(dados, self.nome)
                    if codigo not in CODIGOS_TRANSITORIOS:
                        # Sem o corpo do erro: ele pode ecoar o conteúdo enviado.
                        raise ErroGeracao(f"{self.nome} recusou a chamada (código {codigo})")
                    motivo = f"código {codigo}"

                if tentativa < self._tentativas:
                    logger.warning(
                        "Falha transitória em %s (%s); tentativa %d de %d em %.0fs",
                        self.nome,
                        motivo,
                        tentativa + 1,
                        self._tentativas,
                        espera,
                    )
                    await self._dormir(espera)
                    espera *= 2

        raise ErroGeracao(f"{self.nome} indisponível após {self._tentativas} tentativas ({motivo})")


def _json_de(resposta: httpx.Response) -> dict[str, Any]:
    try:
        dados = resposta.json()
    except ValueError:
        return {}
    return dados if isinstance(dados, dict) else {}


def _codigo_de_erro(resposta: httpx.Response, dados: dict[str, Any]) -> int | str | None:
    """O código do erro, ou `None` quando a chamada deu certo.

    O OpenRouter também devolve erro com status 200, no campo `error` do
    corpo, quando o provedor por trás dele falha depois de aceito o
    pedido. Sem essa leitura, o erro chegaria à geração como resposta
    sem texto.
    """
    if resposta.is_error:
        return resposta.status_code
    erro = dados.get("error")
    if erro is None:
        return None
    codigo = erro.get("code") if isinstance(erro, dict) else None
    return codigo if isinstance(codigo, int) else "desconhecido"


def _texto_de(dados: dict[str, Any], nome: str) -> str:
    """O texto da primeira escolha, ou `ErroGeracao` se não houver — mesma razão do Gemini."""
    try:
        texto = dados["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        texto = None
    if not isinstance(texto, str) or not texto.strip():
        raise ErroGeracao(f"{nome} devolveu resposta vazia (bloqueio do provedor ou sem candidato)")
    return texto
