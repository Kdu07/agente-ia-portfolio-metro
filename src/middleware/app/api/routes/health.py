"""Healthcheck para monitoramento e orquestradores (Docker, k8s).

Duas rotas, porque respondem a perguntas diferentes:

- `/health` — o processo está vivo. Responde na hora, e é o que as sondas
  de início e de vida consultam. Se esperasse o modelo, o orquestrador
  reiniciaria a réplica no meio da carga.
- `/health/pronto` — a réplica já pode receber mensagem. Responde 503
  enquanto o classificador aquece (ver `lifespan` em app/main.py), e é o
  que a sonda de prontidão consulta: o tráfego só chega depois da carga.
"""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter()


@router.get("/health")
async def health() -> dict:
    """Confirma que o serviço está no ar."""
    return {"status": "ok"}


@router.get("/health/pronto")
async def pronto(request: Request) -> JSONResponse:
    """Confirma que o classificador já está carregado.

    Sem aquecimento configurado não há o que esperar, e a réplica está
    pronta desde a subida. Aquecimento que falhou também responde 503: a
    réplica não classificaria nenhuma mensagem, e o motivo está no log.
    """
    aquecimento = getattr(request.app.state, "aquecimento", None)
    if aquecimento is None:
        return JSONResponse({"status": "pronto"})
    if not aquecimento.done():
        return JSONResponse({"status": "aquecendo"}, status_code=503)
    if aquecimento.cancelled() or aquecimento.exception() is not None:
        return JSONResponse({"status": "falhou"}, status_code=503)
    return JSONResponse({"status": "pronto"})
