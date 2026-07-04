"""Integration tests for background scan task transaction handling."""

from __future__ import annotations

import pytest
from sqlalchemy import select

from app.db.session import get_session_factory
from app.main import app
from app.models.enums import ScanJobStatus, ScanType
from app.models.scan_job import ScanJob
from app.services.risk_score import compute_mock_risk_score
from app.services.scan_tasks import run_scan_worker

VALID_ADDRESS = "0x742d35cc6634c0532925a3b844bc9e7595f0beb0"


@pytest.fixture
async def app_lifecycle() -> object:
    """Initialize application database once per test."""
    async with app.router.lifespan_context(app):
        yield


async def _create_pending_scan() -> int:
    session_factory = get_session_factory()
    async with session_factory() as session:
        scan_job = ScanJob(
            scan_type=ScanType.WALLET,
            target_address=VALID_ADDRESS,
            chain_id=11155111,
            status=ScanJobStatus.PENDING,
        )
        session.add(scan_job)
        await session.commit()
        await session.refresh(scan_job)
        return scan_job.id


async def _load_scan(scan_id: int) -> ScanJob:
    session_factory = get_session_factory()
    async with session_factory() as session:
        result = await session.execute(select(ScanJob).where(ScanJob.id == scan_id))
        return result.scalar_one()


@pytest.mark.asyncio
async def test_run_scan_worker_success_persists_completed(app_lifecycle: object) -> None:
    scan_id = await _create_pending_scan()

    await run_scan_worker(scan_id)

    persisted = await _load_scan(scan_id)
    assert persisted.status == ScanJobStatus.COMPLETED
    assert persisted.risk_score == compute_mock_risk_score(ScanType.WALLET, VALID_ADDRESS)


@pytest.mark.asyncio
async def test_run_scan_worker_failure_persists_failed(
    app_lifecycle: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def boom(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("analyzer unavailable")

    monkeypatch.setattr("app.services.scan_worker.compute_mock_risk_score", boom)
    scan_id = await _create_pending_scan()

    with pytest.raises(RuntimeError, match="analyzer unavailable"):
        await run_scan_worker(scan_id)

    persisted = await _load_scan(scan_id)
    assert persisted.status == ScanJobStatus.FAILED
    assert persisted.risk_score is None


@pytest.mark.asyncio
async def test_run_scan_worker_failure_never_reverts_to_pending(
    app_lifecycle: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def boom(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("analyzer unavailable")

    monkeypatch.setattr("app.services.scan_worker.compute_mock_risk_score", boom)
    scan_id = await _create_pending_scan()

    with pytest.raises(RuntimeError):
        await run_scan_worker(scan_id)

    persisted = await _load_scan(scan_id)
    assert persisted.status != ScanJobStatus.PENDING
    assert persisted.status == ScanJobStatus.FAILED


@pytest.mark.asyncio
async def test_run_scan_worker_repeated_invocation_stays_failed(
    app_lifecycle: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def boom(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("analyzer unavailable")

    monkeypatch.setattr("app.services.scan_worker.compute_mock_risk_score", boom)
    scan_id = await _create_pending_scan()

    with pytest.raises(RuntimeError):
        await run_scan_worker(scan_id)

    await run_scan_worker(scan_id)

    persisted = await _load_scan(scan_id)
    assert persisted.status == ScanJobStatus.FAILED


@pytest.mark.asyncio
async def test_run_scan_worker_failure_preserves_database_consistency(
    app_lifecycle: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def boom(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("analyzer unavailable")

    monkeypatch.setattr("app.services.scan_worker.compute_mock_risk_score", boom)
    scan_id = await _create_pending_scan()

    with pytest.raises(RuntimeError):
        await run_scan_worker(scan_id)

    persisted = await _load_scan(scan_id)
    assert persisted.status == ScanJobStatus.FAILED
    assert persisted.chain_id == 11155111
    assert persisted.block_number == 12345678
    assert persisted.rpc_endpoint is not None
    assert persisted.updated_at >= persisted.created_at
