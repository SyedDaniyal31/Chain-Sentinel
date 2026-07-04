"""Health probe at root (load balancer convention)."""

from fastapi import APIRouter, Depends

from app.core.config import Settings, get_settings
from app.schemas.health import HealthResponse
from app.services.health_service import HealthService

router = APIRouter()


def get_health_service(
    settings: Settings = Depends(get_settings),
) -> HealthService:
    return HealthService(settings)


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Root health check",
    include_in_schema=True,
)
async def root_health(
    service: HealthService = Depends(get_health_service),
) -> HealthResponse:
    """Expose GET /health for infrastructure probes (Docker, K8s, uptime)."""
    return service.get_health()
