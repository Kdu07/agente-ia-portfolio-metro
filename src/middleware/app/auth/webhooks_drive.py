"""Valida notificacoes do Drive contra o cadastro local de canais."""

import hashlib
import hmac
import re
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from uuid import UUID

from app.auth.webhooks import WebhookRecusado


@dataclass(frozen=True)
class CanalDrive:
    fonte: str
    token_sha256: bytes = field(repr=False)
    expira_em: float
    recurso_id: str | None = None
    recurso_uri: str | None = None
    pendente: bool = True
    revogado: bool = False

    def __post_init__(self) -> None:
        if len(self.token_sha256) != 32 or not self.fonte:
            raise ValueError("Configuracao de canal invalida")
        if not self.pendente and (not self.recurso_id or not self.recurso_uri):
            raise ValueError("Canal ativo exige recurso confirmado")


@dataclass(frozen=True)
class NotificacaoDrive:
    canal_id: str
    fonte: str
    numero: str
    estado: str

    @property
    def processar(self) -> bool:
        return self.estado == "change"


def verificar_drive(
    cabecalhos: Sequence[tuple[bytes, bytes]],
    corpo: bytes,
    canais: Mapping[str, CanalDrive],
    *,
    fonte: str,
    agora: float | None = None,
) -> NotificacaoDrive:
    """Autentica sem seguir URLs nem alterar o cadastro.

    O receptor limita a leitura a 1 KiB e fornece um cadastro atualizado.
    Canal pendente usa prazo local de inscricao; ativo usa expiracao confirmada.
    Somente processar=True habilita recebimento duravel e publicacao posteriores.
    Deduplicacao usa canal_id e numero; autenticidade nao comprova processamento.
    """
    if len(corpo) > 1024:
        raise WebhookRecusado(413, "WEBHOOK_INVALIDO")
    if corpo:
        raise WebhookRecusado(400, "WEBHOOK_INVALIDO")
    if sum(len(k) + len(v) for k, v in cabecalhos) > 16 * 1024 or any(
        len(v) > 2048 for _, v in cabecalhos
    ):
        raise WebhookRecusado(431, "WEBHOOK_INVALIDO")

    valores = {}
    for nome in (b"channel-id", b"channel-token", b"resource-id", b"resource-uri",
                 b"resource-state", b"message-number"):
        encontrados = [v for k, v in cabecalhos if k.lower() == b"x-goog-" + nome]
        if len(encontrados) > 1:
            raise WebhookRecusado(400, "WEBHOOK_INVALIDO")
        if not encontrados or not encontrados[0]:
            status = 401 if nome == b"channel-token" else 400
            codigo = "WEBHOOK_NAO_AUTORIZADO" if status == 401 else "WEBHOOK_INVALIDO"
            raise WebhookRecusado(status, codigo)
        valor = encontrados[0]
        if any(c < 33 or c > 126 for c in valor):
            raise WebhookRecusado(400, "WEBHOOK_INVALIDO")
        valores[nome] = valor.decode("ascii")

    identificador = valores[b"channel-id"]
    try:
        if str(UUID(identificador)) != identificador.lower():
            raise ValueError
    except ValueError:
        raise WebhookRecusado(400, "WEBHOOK_INVALIDO") from None
    numero = valores[b"message-number"]
    if not re.fullmatch(r"[0-9]{1,64}", numero) or int(numero) == 0:
        raise WebhookRecusado(400, "WEBHOOK_INVALIDO")
    token = valores[b"channel-token"]
    if len(token) > 256:
        raise WebhookRecusado(400, "WEBHOOK_INVALIDO")
    estado = valores[b"resource-state"]
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]*", estado):
        raise WebhookRecusado(400, "WEBHOOK_INVALIDO")
    estado = "change" if estado == "changed" else estado
    instante = time.time() if agora is None else agora
    canal = canais.get(identificador)
    if (
        canal is None or canal.revogado or canal.fonte != fonte
        or instante >= canal.expira_em
        or not hmac.compare_digest(
            hashlib.sha256(token.encode("ascii")).digest(), canal.token_sha256
        )
    ):
        raise WebhookRecusado(401, "WEBHOOK_NAO_AUTORIZADO")

    if canal.pendente:
        if estado != "sync":
            raise WebhookRecusado(503, "WEBHOOK_INDISPONIVEL")
    elif (
        valores[b"resource-id"] != canal.recurso_id
        or valores[b"resource-uri"] != canal.recurso_uri
    ):
        raise WebhookRecusado(401, "WEBHOOK_NAO_AUTORIZADO")
    return NotificacaoDrive(identificador, canal.fonte, str(int(numero)), estado)
