"""Scan job business logic."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.blockchain.chain_registry import ChainRegistry, get_chain_registry
from app.core.exceptions import ScanNotFoundError, UnsupportedChainError
from app.models.enums import ScanJobStatus, ScanType
from app.models.scan_job import ScanJob
from app.repositories.scan_repository import PaginatedScanJobs, ScanRepository, ScanSummaryStats
from app.schemas.scan import PaginatedScanListResponse, ScanListItemResponse, ScanSummaryResponse


class ScanService:
    """Creates and manages scan jobs."""

    def __init__(
        self,
        session: AsyncSession,
        registry: ChainRegistry | None = None,
    ) -> None:
        self._session = session
        self._repository = ScanRepository(session)
        self._registry = registry or get_chain_registry()

    async def create_scan(
        self,
        scan_type: ScanType,
        target_address: str,
        chain_id: int,
    ) -> ScanJob:
        """Queue a new scan job in pending state."""
        self._registry.get(chain_id)

        scan_job = ScanJob(
            scan_type=scan_type,
            target_address=target_address,
            chain_id=chain_id,
            status=ScanJobStatus.PENDING,
            risk_score=None,
        )
        self._session.add(scan_job)
        await self._session.flush()
        await self._session.refresh(scan_job)
        return scan_job

    async def get_scan_by_id(self, scan_id: int) -> ScanJob:
        """Fetch a scan job by primary key."""
        result = await self._session.execute(
            select(ScanJob)
            .options(selectinload(ScanJob.result))
            .where(ScanJob.id == scan_id)
        )
        scan_job = result.scalar_one_or_none()
        if scan_job is None:
            raise ScanNotFoundError(scan_id)
        return scan_job

    async def list_scans(self, *, page: int, page_size: int) -> PaginatedScanListResponse:
        """Return a paginated scan history sorted newest-first."""
        page_result = await self._repository.list_scans_paginated(
            page=page,
            page_size=page_size,
        )
        return _to_paginated_response(page_result)

    async def get_scan_summary(self) -> ScanSummaryResponse:
        """Return aggregate scan intelligence metrics."""
        stats = await self._repository.get_summary_stats()
        return ScanSummaryResponse.model_validate(stats)


def _to_paginated_response(page_result: PaginatedScanJobs) -> PaginatedScanListResponse:
    items = [_to_list_item(scan_job) for scan_job in page_result.items]
    return PaginatedScanListResponse(
        items=items,
        total=page_result.total,
        page=page_result.page,
        page_size=page_result.page_size,
        total_pages=page_result.total_pages,
    )


def _to_list_item(scan_job: ScanJob) -> ScanListItemResponse:
    risk_level = scan_job.result.risk_level if scan_job.result else None
    return ScanListItemResponse(
        id=scan_job.id,
        scan_type=scan_job.scan_type,
        target_address=scan_job.target_address,
        status=scan_job.status,
        risk_score=scan_job.risk_score,
        risk_level=risk_level,
        created_at=scan_job.created_at,
    )
