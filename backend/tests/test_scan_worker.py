"""ScanWorker unit tests."""

import pytest
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.base import Base
from app.models.enums import RiskLevel, ScanDetectionMethod, ScanJobStatus, ScanType
from app.models.scan_job import ScanJob
from app.models.scan_result import ScanResult
from app.services.risk_score import compute_mock_risk_score
from app.services.scan_worker import ScanWorker

VALID_ADDRESS = "0x742d35cc6634c0532925a3b844bc9e7595f0beb0"


@pytest.fixture
async def db_session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        session.add(
            ScanJob(
                scan_type=ScanType.WALLET,
                target_address=VALID_ADDRESS,
                chain_id=11155111,
                status=ScanJobStatus.PENDING,
            )
        )
        await session.commit()

        async with session_factory() as worker_session:
            yield worker_session

    await engine.dispose()


@pytest.mark.asyncio
async def test_scan_worker_pending_to_completed(db_session: AsyncSession) -> None:
    worker = ScanWorker(db_session)
    scan_job = await worker.process(1)
    await db_session.commit()

    assert scan_job.status == ScanJobStatus.COMPLETED
    assert scan_job.risk_score == compute_mock_risk_score(ScanType.WALLET, VALID_ADDRESS)

    db_result = await db_session.execute(select(ScanResult).where(ScanResult.scan_job_id == 1))
    scan_result = db_result.scalar_one()
    assert scan_result.chain_id == 11155111
    assert scan_result.latest_block == 12345678
    assert scan_result.wallet_balance_wei == 1000000000000000000
    assert scan_result.analyzer_version == "1.1.0"
    assert scan_job.chain_id == 11155111
    assert scan_job.block_number == 12345678
    assert scan_job.rpc_endpoint is not None


@pytest.mark.asyncio
async def test_mock_risk_score_is_deterministic() -> None:
    score_a = compute_mock_risk_score(ScanType.WALLET, VALID_ADDRESS)
    score_b = compute_mock_risk_score(ScanType.WALLET, VALID_ADDRESS)

    assert score_a == score_b
    assert 0 <= score_a <= 100


@pytest.mark.asyncio
async def test_scan_worker_marks_failed_on_error(
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def boom(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("analyzer unavailable")

    monkeypatch.setattr(
        "app.services.scan_worker.compute_mock_risk_score",
        boom,
    )

    worker = ScanWorker(db_session)
    with pytest.raises(RuntimeError, match="analyzer unavailable"):
        await worker.process(1)
    await db_session.commit()

    refreshed = await worker._load_scan(1)
    assert refreshed.status == ScanJobStatus.FAILED
    assert refreshed.risk_score is None


@pytest.fixture
async def contract_db_session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        session.add(
            ScanJob(
                scan_type=ScanType.CONTRACT,
                target_address="0x1f9840a85d5af5bf1d1762f925bdaddc4201f984",
                chain_id=11155111,
                status=ScanJobStatus.PENDING,
            )
        )
        await session.commit()

        async with session_factory() as worker_session:
            yield worker_session

    await engine.dispose()


@pytest.mark.asyncio
async def test_scan_worker_contract_pending_to_completed(contract_db_session: AsyncSession) -> None:
    worker = ScanWorker(contract_db_session)
    scan_job = await worker.process(1)
    await contract_db_session.commit()

    assert scan_job.status == ScanJobStatus.COMPLETED
    assert scan_job.risk_score == Decimal("0.00")

    db_result = await contract_db_session.execute(
        select(ScanResult).where(ScanResult.scan_job_id == 1)
    )
    scan_result = db_result.scalar_one()
    assert scan_result.is_contract is True
    assert scan_result.bytecode_size == 24576
    assert scan_result.is_upgradeable is False
    assert scan_result.implementation_address is None
    assert scan_result.admin_address is None
    assert scan_result.risk_level == RiskLevel.LOW
    assert scan_result.risk_reasons == ["No upgradeability indicators detected"]
    assert scan_result.wallet_balance_wei is None
    assert scan_result.detection_method == ScanDetectionMethod.BYTECODE
    assert scan_result.analyzer_version == "1.1.0"
    assert scan_job.chain_id == 11155111
    assert scan_job.block_number == 12345678
