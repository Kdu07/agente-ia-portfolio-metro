"""Rotas de entrada dos webhooks (Projeto.md, seção 9.1.2.7).

Sem cookie de usuário: a autenticidade é a do emissor, verificada em
`app/auth/webhooks*.py`. A regra de negócio não roda aqui: a rota
registra, publica e responde; o processamento é do consumidor (#394).

As respostas de sucesso são vazias. Os erros usam
`{"detail": {"codigo": ..., "mensagem": ...}}` com mensagens genéricas,
que não dizem qual comparação de autenticação falhou nem expõem token,
canal ou documento. `405` vem do próprio roteador, com `Allow: POST`.
"""

import logging

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse

from app.api.deps import FabricaSessoes, Produtor
from app.auth.webhooks import WebhookRecusado
from app.config import settings
from app.webhooks.drive.recebimento import receber_notificacao

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks")

# O Drive envia corpo vazio. Ler além disso só gastaria memória com um
# corpo que será recusado de qualquer jeito.
LIMITE_CORPO_DRIVE = 1024

MENSAGENS = {
    "WEBHOOK_INVALIDO": "Notificação inválida.",
    "WEBHOOK_NAO_AUTORIZADO": "Notificação não autorizada.",
    "WEBHOOK_INDISPONIVEL": "Serviço temporariamente indisponível.",
    "WEBHOOK_ERRO_INTERNO": "Erro interno ao processar a notificação.",
}


class _CorpoGrande(Exception):
    pass


async def _ler_corpo(request: Request, limite: int) -> bytes:
    """Lê o corpo até `limite` bytes e interrompe a leitura se passar disso."""
    corpo = bytearray()
    async for pedaco in request.stream():
        corpo.extend(pedaco)
        if len(corpo) > limite:
            raise _CorpoGrande
    return bytes(corpo)


def _erro(status: int, codigo: str) -> JSONResponse:
    cabecalhos = {"Retry-After": "5"} if status == 503 else None
    return JSONResponse(
        status_code=status,
        content={"detail": {"codigo": codigo, "mensagem": MENSAGENS[codigo]}},
        headers=cabecalhos,
    )


@router.post(
    "/google-drive",
    status_code=202,
    responses={
        202: {"description": "Mudança registrada e publicada para processamento"},
        204: {"description": "`sync`, estado ignorado ou repetição já publicada"},
        400: {"description": "Cabeçalho ausente, repetido ou malformado, ou corpo não vazio"},
        401: {"description": "Token, canal, validade ou recurso não conferem"},
        413: {"description": "Corpo acima do limite"},
        431: {"description": "Cabeçalhos acima do limite"},
        503: {"description": "Banco, broker ou orçamento de 3 s indisponível; repetir"},
    },
)
async def receber_google_drive(
    request: Request, produtor: Produtor, fabrica: FabricaSessoes
) -> Response:
    """Recebe a notificação `changes.watch` do Drive (WH-01)."""
    try:
        corpo = await _ler_corpo(request, LIMITE_CORPO_DRIVE)
        status = await receber_notificacao(
            request.headers.raw,
            corpo,
            fabrica=fabrica,
            produtor=produtor,
            fonte_id=settings.drive_webhook_fonte,
        )
    except _CorpoGrande:
        return _erro(413, "WEBHOOK_INVALIDO")
    except WebhookRecusado as recusa:
        return _erro(recusa.status, recusa.codigo)
    except Exception:
        logger.exception("Falha inesperada no webhook do Drive")
        return _erro(500, "WEBHOOK_ERRO_INTERNO")
    return Response(status_code=status)
