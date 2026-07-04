"""Verify PostgreSQL schema revision matches Alembic head at startup."""

from __future__ import annotations

import logging
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

logger = logging.getLogger(__name__)


async def verify_migration_head(engine: AsyncEngine) -> None:
    """Fail fast when the database revision lags Alembic head."""
    if engine.dialect.name != "postgresql":
        return

    alembic_cfg = Config(str(Path(__file__).resolve().parents[2] / "alembic.ini"))
    script = ScriptDirectory.from_config(alembic_cfg)
    expected_head = script.get_current_head()

    async with engine.connect() as connection:
        db_revision = await connection.scalar(text("SELECT version_num FROM alembic_version"))

    if db_revision != expected_head:
        raise RuntimeError(
            "Database schema is out of date: "
            f"alembic_version={db_revision!r}, head={expected_head!r}. "
            "Run: alembic upgrade head"
        )

    logger.info("Database migration revision verified (head=%s)", expected_head)
