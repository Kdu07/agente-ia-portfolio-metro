"""Healthcheck para monitoramento e orquestradores (Docker, k8s)."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health() -> dict:
    """Confirma que o serviço está no ar."""
    return {"status": "ok"}
