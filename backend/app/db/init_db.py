"""Database schema initialization and connectivity checks."""

import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.db.base import Base

logger = logging.getLogger(__name__)


async def create_tables(engine: AsyncEngine) -> None:
    """Create all ORM tables (development bootstrap only)."""
    # Import models so they register on Base.metadata before create_all.
    import app.models  # noqa: F401

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    logger.info("Database tables ensured via metadata.create_all")


async def verify_connection(engine: AsyncEngine) -> None:
    """Verify the database is reachable at startup."""
    async with engine.connect() as connection:
        await connection.execute(text("SELECT 1"))
    logger.info("Database connection verified")
