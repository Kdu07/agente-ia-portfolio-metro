"""Classificador de intenções.

Mapeia a mensagem (já aprovada pelas guardas de entrada) para uma
intenção do catálogo, devolvendo o rótulo e a confiança que o
orquestrador compara com `Intencao.limiar_confianca`.

O modelo é o ensemble de TF-IDF com embeddings multilíngues descrito em
modelo.py, treinado por treino.py e carregado uma única vez por processo.
O carregamento é preguiçoso e protegido por lock: sob concorrência, a
primeira requisição que chega inicializa e as demais esperam, em vez de
cada uma instanciar um encoder de 2 GB.

**Por que a inferência sai da thread do event loop.** `predict_proba` é
CPU-bound e leva centenas de milissegundos; executá-la direto numa
corrotina bloquearia o event loop inteiro do FastAPI, e o efeito
apareceria como latência em toda requisição concorrente, não só nesta.
`asyncio.to_thread` a joga num worker — e o GIL é liberado durante a
inferência do torch e do numpy, então o paralelismo é real.

O pré-processamento acontece dentro do pipeline (primeiro passo), e não
aqui: é o que garante que treino e inferência não divirjam. Este módulo
recebe o texto como o usuário o escreveu.
"""

import asyncio
import logging
import threading
import time
from dataclasses import dataclass

from app.config import settings
from app.pipeline.intencao import treino
from app.pipeline.intencao.treino import ArtefatoTreinado

logger = logging.getLogger(__name__)

_artefato: ArtefatoTreinado | None = None
_lock = threading.Lock()


@dataclass
class ResultadoIntencao:
    """Intenção classificada para uma mensagem."""

    intencao_id: str | None  # None quando nenhuma intenção do catálogo se aplica
    confianca: float  # 0.0 a 1.0


def obter_artefato() -> ArtefatoTreinado:
    """Devolve o modelo treinado, carregando-o na primeira chamada."""
    global _artefato
    if _artefato is None:
        with _lock:
            # Segunda checagem sob o lock: entre a primeira e a aquisição,
            # outra thread pode já ter carregado.
            if _artefato is None:
                _artefato = treino.carregar()
                logger.info(
                    "Classificador carregado (%d classes, treinado em %s)",
                    len(_artefato.classes),
                    _artefato.treinado_em,
                )
    return _artefato


def limiar_de(intencao_id: str) -> float | None:
    """Limiar calibrado para uma intenção, se o artefato trouxer um.

    Devolve None quando o modelo foi treinado sem calibração — nesse caso
    quem chama deve cair no `Intencao.limiar_confianca` do catálogo.
    """
    if settings.performance_mode:
        return None
    return obter_artefato().limiares.get(intencao_id)


def _classificar_sincrono(texto: str) -> ResultadoIntencao:
    artefato = obter_artefato()
    probabilidades = artefato.pipeline.predict_proba([texto])[0]
    indice = int(probabilidades.argmax())
    return ResultadoIntencao(
        intencao_id=str(artefato.pipeline.classes_[indice]),
        confianca=float(probabilidades[indice]),
    )


def aquecer() -> None:
    """Carrega o artefato e o encoder antes da primeira mensagem.

    Carregar o artefato não basta: o encoder de ~2 GB só sobe na primeira
    `transform` (ver `EmbeddingsSentenca`). Uma classificação descartável
    força as duas cargas. Sem isso, a primeira mensagem de cada réplica
    paga minutos de carga, perto do limite de 240 s do ingress do
    Container Apps.
    """
    inicio = time.perf_counter()
    try:
        _classificar_sincrono("aquecimento do classificador")
    except Exception:
        logger.exception("Falha ao aquecer o classificador")
        raise
    logger.info("Classificador aquecido em %.1f s", time.perf_counter() - inicio)


async def classificar(texto: str) -> ResultadoIntencao:
    """Classifica o texto contra o catálogo de intenções.

    Uma mensagem vazia não é classificada: devolve `intencao_id=None`,
    que o orquestrador já trata como fora de escopo. Chamar o modelo com
    string vazia produziria uma classe arbitrária com confiança alta.
    """
    if not texto or not texto.strip():
        return ResultadoIntencao(intencao_id=None, confianca=0.0)
    if settings.performance_mode:
        return ResultadoIntencao(intencao_id="consultar_status_projeto", confianca=0.99)
    return await asyncio.to_thread(_classificar_sincrono, texto)
