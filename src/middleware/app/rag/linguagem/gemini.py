"""Adaptador do modelo de geração — Gemini, pelo SDK `google-genai`.

Decisão D3 do plano: provisionamento imediato e camada gratuita
suficiente para um MVP sobre dado sintético. O custo assumido é o mais
sério do plano — a pergunta e os trechos recuperados saem para o Google
a cada consulta —, e está registrado na seção 4.5 e na matriz de riscos.

Três escolhas deste módulo que não são preferência de estilo:

- **instrução e conteúdo viajam por canais distintos.** As regras vão em
  `system_instruction`; a pergunta e os trechos, em `contents`. É a
  fronteira da seção 4.4 materializada no protocolo do provedor, e é o
  que a porta (`base.py`) exige de todo adaptador;
- **novas tentativas só para o que é transitório.** Cota por minuto
  (429) e indisponibilidade (5xx, tempo esgotado) passam sozinhas; chave
  inválida ou pedido malformado (demais 4xx) não passam, e repetir só
  atrasaria o erro. É o risco "limite de taxa do Gemini" da seção 8 do
  plano: sem espera, a bancada falha pela metade e parece defeito do RAG;
- **temperatura no padrão do provedor.** A família Gemini 3 é calibrada
  para a temperatura padrão, e reduzi-la pode degradar o raciocínio. O
  que mantém a resposta presa ao contexto são as instruções de
  `geracao.py` e a verificação das citações, não a amostragem.

O cliente do SDK é injetado — os testes o dublam sem rede nem chave — e
criado uma vez por processo por `de_configuracao`.
"""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from app.config import settings
from app.rag.linguagem.base import ErroGeracao

logger = logging.getLogger(__name__)

# Códigos HTTP em que tentar de novo tem chance de dar certo: cota por
# minuto esgotada e indisponibilidade do serviço.
CODIGOS_TRANSITORIOS = frozenset({429, 500, 502, 503, 504})

# Tentativas no total, a primeira inclusa, com espera que dobra: 2 s, 4 s,
# 8 s. Somam ~14 s, o bastante para a janela de cota por minuto começar a
# se renovar sem prender a requisição do usuário por mais de meio minuto.
TENTATIVAS = 4
ESPERA_INICIAL = 2.0


class ModeloGemini:
    """Implementa `ModeloLinguagem` sobre a API do Gemini."""

    def __init__(
        self,
        cliente: Any,
        modelo: str,
        *,
        timeout: float,
        tentativas: int = TENTATIVAS,
        espera_inicial: float = ESPERA_INICIAL,
        dormir: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        """Recebe o cliente pronto. `dormir` existe para os testes não esperarem."""
        self._cliente = cliente
        self._modelo = modelo
        self._timeout = timeout
        self._tentativas = max(1, tentativas)
        self._espera_inicial = espera_inicial
        self._dormir = dormir

    @classmethod
    def de_configuracao(cls) -> "ModeloGemini":
        """Monta o adaptador a partir do `.env`, conferindo a chave antes do import.

        Mesma disciplina de `RepositorioPinecone.de_configuracao`: chave
        ausente e extra `rag` não instalado são nomeados aqui, e não numa
        chamada de rede sem contexto.
        """
        if not settings.gemini_api_key:
            raise RuntimeError("gemini_api_key é obrigatória com llm_backend=gemini")
        try:
            from google import genai
        except ModuleNotFoundError as erro:  # pragma: no cover - depende do ambiente
            raise RuntimeError(
                "llm_backend=gemini exige o extra `rag`: pip install -e '.[rag]'"
            ) from erro

        cliente = genai.Client(api_key=settings.gemini_api_key)
        return cls(cliente, settings.gemini_modelo, timeout=settings.gemini_timeout_seconds)

    @property
    def nome(self) -> str:
        return f"gemini/{self._modelo}"

    async def gerar(self, *, instrucoes: str, conteudo: str) -> str:
        """Chama o modelo, repetindo as falhas transitórias com espera crescente.

        O cliente assíncrono do SDK (`cliente.aio`) é nativo, então não
        há `to_thread` aqui, ao contrário do Pinecone. O teto de tempo é
        aplicado por tentativa com `wait_for`, e não pela opção HTTP do
        SDK, para valer igual em qualquer versão dele.
        """
        espera = self._espera_inicial
        for tentativa in range(1, self._tentativas + 1):
            try:
                resposta = await asyncio.wait_for(
                    self._cliente.aio.models.generate_content(
                        model=self._modelo,
                        contents=conteudo,
                        config={"system_instruction": instrucoes},
                    ),
                    timeout=self._timeout,
                )
            except TimeoutError:
                motivo = f"tempo esgotado ({self._timeout:.0f}s)"
            except Exception as erro:
                # Genérico de propósito: o SDK tem hierarquia própria de
                # erros, e o que decide aqui é só o código HTTP em `.code`.
                codigo = getattr(erro, "code", None)
                if codigo not in CODIGOS_TRANSITORIOS:
                    # Sem a mensagem do erro: ela pode ecoar o conteúdo enviado.
                    raise ErroGeracao(
                        f"{self.nome} recusou a chamada ({type(erro).__name__}, código {codigo})"
                    ) from erro
                motivo = f"código {codigo}"
            else:
                return _texto_de(resposta, self.nome)

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


def _texto_de(resposta: Any, nome: str) -> str:
    """O texto da resposta, ou `ErroGeracao` se não houver.

    `.text` vem `None` quando o provedor bloqueia a resposta pelos
    próprios filtros de segurança ou a interrompe sem candidato. Tratar
    isso como string vazia faria a geração ler "resposta sem citação" e
    abster-se — escondendo um bloqueio do provedor atrás de uma recusa
    que parece legítima.
    """
    texto = getattr(resposta, "text", None)
    if not texto or not texto.strip():
        raise ErroGeracao(f"{nome} devolveu resposta vazia (bloqueio do provedor ou sem candidato)")
    return texto
