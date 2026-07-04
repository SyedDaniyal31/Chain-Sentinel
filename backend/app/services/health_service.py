"""Health check business logic."""

from app import __version__
from app.core.config import Settings
from app.schemas.health import HealthResponse


class HealthService:
    """Builds health probe payloads."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def get_health(self) -> HealthResponse:
        """Return the current service health snapshot."""
        return HealthResponse(
            status="healthy",
            service=self._settings.app_name,
            version=__version__,
        )
