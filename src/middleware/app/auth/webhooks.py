"""Autenticidade de eventos externos, antes do parsing e dos efeitos de negocio."""

import base64
import binascii
import hashlib
import hmac
import re
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field


@dataclass(frozen=True)
class ChavePortfolio:
    segredo: bytes = field(repr=False)
    valida_desde: int
    valida_ate: int
    revogada: bool = False

    def __post_init__(self) -> None:
        if len(self.segredo) != 32 or self.valida_ate <= self.valida_desde:
            raise ValueError("Configuracao de chave de webhook invalida")


class WebhookRecusado(ValueError):
    def __init__(self, status: int, codigo: str) -> None:
        self.status = status
        self.codigo = codigo
        super().__init__(codigo)


def verificar_portfolio(
    cabecalhos: Sequence[tuple[bytes, bytes]],
    corpo: bytes,
    chaves: Mapping[tuple[str, str], ChavePortfolio],
    *,
    agora: float | None = None,
) -> str:
    """Devolve a fonte autenticada usando headers ASGI e corpo bruto.

    O receptor deve limitar a leitura do corpo a 32 KiB antes desta chamada,
    conferir source_id no JSON e autorizar a entidade antes de aplicar efeitos.
    Autenticidade nao substitui deduplicacao duravel nem validacao de schema.
    O cadastro de chaves deve refletir revogacoes a cada recebimento.
    """
    if len(corpo) > 32 * 1024:
        raise WebhookRecusado(413, "WEBHOOK_INVALIDO")
    if sum(len(k) + len(v) for k, v in cabecalhos) > 16 * 1024 or any(
        len(v) > 2 * 1024 for _, v in cabecalhos
    ):
        raise WebhookRecusado(431, "WEBHOOK_INVALIDO")

    valores = {}
    for nome in (b"x-prata-source", b"x-prata-key-id", b"x-prata-timestamp",
                 b"x-prata-signature"):
        encontrados = [v for k, v in cabecalhos if k.lower() == nome]
        if len(encontrados) > 1:
            raise WebhookRecusado(400, "WEBHOOK_INVALIDO")
        if not encontrados or not encontrados[0]:
            raise WebhookRecusado(401, "WEBHOOK_NAO_AUTORIZADO")
        try:
            valores[nome] = encontrados[0].decode("ascii")
        except UnicodeDecodeError:
            raise WebhookRecusado(400, "WEBHOOK_INVALIDO") from None

    fonte = valores[b"x-prata-source"]
    identificador = valores[b"x-prata-key-id"]
    timestamp = valores[b"x-prata-timestamp"]
    if not all(re.fullmatch(r"[A-Za-z0-9_-]{1,64}", v) for v in (fonte, identificador)):
        raise WebhookRecusado(400, "WEBHOOK_INVALIDO")
    if not re.fullmatch(r"0|[1-9][0-9]*", timestamp):
        raise WebhookRecusado(400, "WEBHOOK_INVALIDO")

    instante = time.time() if agora is None else agora
    chave = chaves.get((fonte, identificador))
    if (
        not instante - 300 <= int(timestamp) <= instante + 300
        or chave is None
        or chave.revogada
        or not chave.valida_desde <= instante < chave.valida_ate
    ):
        raise WebhookRecusado(401, "WEBHOOK_NAO_AUTORIZADO")

    try:
        assinatura = base64.b64decode(valores[b"x-prata-signature"], validate=True)
    except (ValueError, binascii.Error):
        raise WebhookRecusado(401, "WEBHOOK_NAO_AUTORIZADO") from None
    entrada = f"{fonte}\n{identificador}\n{timestamp}\n".encode("ascii") + corpo
    esperada = hmac.digest(chave.segredo, entrada, hashlib.sha256)
    if len(assinatura) != 32 or not hmac.compare_digest(assinatura, esperada):
        raise WebhookRecusado(401, "WEBHOOK_NAO_AUTORIZADO")
    return fonte
