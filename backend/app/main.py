"""ChainSentinel API entrypoint."""

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api.health import router as health_router
from app.api.v1.router import api_v1_router
from app.core.config import get_settings
from app.core.exception_handlers import register_exception_handlers
from app.core.logging import configure_logging
from app.db.init_db import create_tables, verify_connection
from app.db.migration_check import verify_migration_head
from app.db.session import close_db, init_db

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Startup and shutdown hooks."""
    settings = get_settings()
    configure_logging(settings)

    engine = init_db(settings)

    try:
        await verify_connection(engine)
        if not settings.database_url.startswith("sqlite"):
            await verify_migration_head(engine)
        if settings.db_auto_create_tables:
            await create_tables(engine)
    except Exception:
        logger.exception("Database startup failed — check DATABASE_URL and PostgreSQL")
        raise

    yield
    await close_db()


def create_app() -> FastAPI:
    """Application factory."""
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=__version__,
        description="Blockchain Security Intelligence Platform API",
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        openapi_url="/openapi.json" if not settings.is_production else None,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    app.include_router(health_router)
    app.include_router(api_v1_router)

    register_exception_handlers(app, settings)

    return app


app = create_app()
