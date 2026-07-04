"""Database engine and session factory."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.config import Settings

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def init_db(settings: Settings) -> AsyncEngine:
    """Initialize the async engine and session factory."""
    global _engine, _session_factory

    engine_kwargs: dict = {
        "echo": settings.app_debug,
        "pool_pre_ping": True,
    }
    if settings.database_url.startswith("sqlite"):
        # Share a single in-memory database across connections (required for BackgroundTasks).
        engine_kwargs["connect_args"] = {"check_same_thread": False}
        engine_kwargs["poolclass"] = StaticPool
    else:
        engine_kwargs["pool_size"] = settings.db_pool_size
        engine_kwargs["max_overflow"] = settings.db_max_overflow

    _engine = create_async_engine(settings.database_url, **engine_kwargs)
    _session_factory = async_sessionmaker(
        bind=_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
    return _engine


def get_engine() -> AsyncEngine:
    """Return the active async engine."""
    if _engine is None:
        raise RuntimeError("Database is not initialized. Call init_db() during startup.")
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return the active session factory for background workers."""
    if _session_factory is None:
        raise RuntimeError("Database is not initialized. Call init_db() during startup.")
    return _session_factory


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields a database session."""
    if _session_factory is None:
        raise RuntimeError("Database is not initialized. Call init_db() during startup.")

    async with _session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def close_db() -> None:
    """Dispose of the database engine on shutdown."""
    global _engine, _session_factory

    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_factory = None


__all__ = ["init_db", "get_engine", "get_session_factory", "get_db", "close_db"]
