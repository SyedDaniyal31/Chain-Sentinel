"""Background task entrypoints for scan processing."""

import logging

from app.db.session import get_session_factory
from app.services.scan_worker import ScanWorker

logger = logging.getLogger(__name__)


async def run_scan_worker(scan_id: int) -> None:
    """
    Process a scan job in a dedicated database session.

    Called from FastAPI BackgroundTasks after the HTTP response is sent.
    Must not reuse the request-scoped session — it is closed by then.
    """
    session_factory = get_session_factory()

    async with session_factory() as session:
        try:
            worker = ScanWorker(session)
            await worker.process(scan_id)
            await session.commit()
        except Exception:
            # ScanWorker flushes FAILED (and other lifecycle updates) before re-raising.
            # rollback() would discard those writes and leave the job stuck in pending.
            await session.commit()
            logger.exception("Background scan worker failed for scan_id=%s", scan_id)
            raise
