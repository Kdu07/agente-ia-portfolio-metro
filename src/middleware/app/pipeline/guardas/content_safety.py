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

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

API_VERSION = "2024-09-01"
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


_cliente: httpx.AsyncClient | None = None
_semaforo: asyncio.Semaphore | None = None
_limitador: "_LimitadorTaxa | None" = None


class _LimitadorTaxa:
    """Espaça o início das chamadas para respeitar a quota por processo."""

    def __init__(self, requisicoes_por_segundo: float) -> None:
        self._intervalo = 0.0 if requisicoes_por_segundo <= 0 else 1 / requisicoes_por_segundo
        self._proxima = 0.0
        self._lock = asyncio.Lock()

    async def esperar(self) -> None:
        if self._intervalo == 0:
            return
        async with self._lock:
            agora = asyncio.get_running_loop().time()
            espera = max(0.0, self._proxima - agora)
            if espera:
                await asyncio.sleep(espera)
            self._proxima = asyncio.get_running_loop().time() + self._intervalo


def _limites() -> httpx.Limits:
    limite = settings.content_safety_max_concorrencia
    return httpx.Limits(max_connections=limite, max_keepalive_connections=limite)


async def iniciar() -> None:
    """Cria um único pool HTTP para todas as guardas do processo."""
    global _cliente, _limitador, _semaforo
    if _cliente is not None:
        return
    _cliente = httpx.AsyncClient(
        timeout=settings.content_safety_timeout_seconds,
        limits=_limites(),
    )
    _semaforo = asyncio.Semaphore(settings.content_safety_max_concorrencia)
    _limitador = _LimitadorTaxa(settings.content_safety_requisicoes_por_segundo)


async def encerrar() -> None:
    """Fecha o pool HTTP compartilhado no encerramento da aplicação."""
    global _cliente, _limitador, _semaforo
    if _cliente is not None:
        await _cliente.aclose()
    _cliente = None
    _semaforo = None
    _limitador = None


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
    _semaforo: asyncio.Semaphore
    _limitador: _LimitadorTaxa

    async def analisar(self, operacao: str, corpo: dict) -> dict:
        """Chama uma operação do Content Safety e devolve o corpo JSON.

        `operacao` é o segmento final da rota (`text:shieldPrompt`,
        `text:analyze`). Levanta `Indisponivel` em qualquer caminho que
        não termine num veredito legível.
        """
        url = f"{settings.content_safety_endpoint.rstrip('/')}/contentsafety/{operacao}"
        cabecalhos = {"Ocp-Apim-Subscription-Key": settings.content_safety_key}
        try:
            async with asyncio.timeout(settings.content_safety_fila_timeout_seconds):
                await self._semaforo.acquire()
        except TimeoutError:
            raise Indisponivel("capacidade local esgotada") from None

        try:
            resposta = await self._postar_com_retentativa(url, cabecalhos, corpo)
        finally:
            self._semaforo.release()

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

    async def _postar_com_retentativa(
        self, url: str, cabecalhos: dict[str, str], corpo: dict
    ) -> httpx.Response:
        """Repete apenas falhas transitórias, respeitando `Retry-After`.

        A espera pedida pelo serviço vale até o tempo limite de uma chamada.
        Acima disso, desiste na hora e devolve a resposta de erro, que a
        guarda trata como indisponibilidade.
        """
        ultima: httpx.Response | None = None
        for tentativa in range(settings.content_safety_max_tentativas):
            try:
                await self._limitador.esperar()
                resposta = await self._cliente.post(
                    url,
                    params={"api-version": API_VERSION},
                    json=corpo,
                    headers=cabecalhos,
                )
            except httpx.TimeoutException:
                if tentativa + 1 == settings.content_safety_max_tentativas:
                    raise Indisponivel(
                        f"tempo esgotado ({settings.content_safety_timeout_seconds:g}s)"
                    ) from None
                await asyncio.sleep(_espera(None, tentativa))
                continue
            except httpx.TransportError as erro:
                if tentativa + 1 == settings.content_safety_max_tentativas:
                    raise Indisponivel(f"falha de rede ({type(erro).__name__})") from None
                await asyncio.sleep(_espera(None, tentativa))
                continue

            ultima = resposta
            if resposta.status_code not in {429, 502, 503, 504}:
                return resposta
            if tentativa + 1 < settings.content_safety_max_tentativas:
                espera = _espera(resposta, tentativa)
                # Repetir antes do prazo pedido só renderia outro 429 e gastaria
                # cota; esperar o prazo inteiro prenderia a vaga do semáforo e
                # derrubaria por fila quem está atrás. Sem as duas coisas, a
                # guarda falha fechada agora, como numa indisponibilidade.
                if espera > settings.content_safety_timeout_seconds:
                    return resposta
                await asyncio.sleep(espera)

        assert ultima is not None
        return ultima


def _espera(resposta: httpx.Response | None, tentativa: int) -> float:
    """Espera indicada pelo Azure ou recuo exponencial curto."""
    if resposta is not None:
        try:
            return max(0.0, float(resposta.headers.get("Retry-After", "")))
        except ValueError:
            pass
    return settings.content_safety_espera_base_seconds * (2**tentativa)


@asynccontextmanager
async def sessao(transporte: httpx.AsyncBaseTransport | None = None) -> AsyncIterator[Sessao]:
    """Abre uma sessão HTTP para as chamadas de uma avaliação.

    `transporte` existe para os testes dublarem o serviço sem rede, e é o
    mesmo parâmetro que as três guardas expõem.
    """
    if transporte is not None:
        async with httpx.AsyncClient(
            timeout=settings.content_safety_timeout_seconds,
            transport=transporte,
        ) as cliente:
            yield Sessao(
                cliente,
                asyncio.Semaphore(settings.content_safety_max_concorrencia),
                _LimitadorTaxa(0),
            )
        return

    if _cliente is None or _semaforo is None or _limitador is None:
        await iniciar()
    assert _cliente is not None and _semaforo is not None and _limitador is not None
    yield Sessao(_cliente, _semaforo, _limitador)
