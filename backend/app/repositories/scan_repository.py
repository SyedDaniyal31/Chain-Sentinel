"""Data access layer for scan job listing and analytics."""

import math
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.enums import RiskLevel, ScanJobStatus
from app.models.scan_job import ScanJob
from app.models.scan_result import ScanResult


@dataclass(frozen=True, slots=True)
class PaginatedScanJobs:
    """Repository result for a paginated scan listing."""

    items: list[ScanJob]
    total: int
    page: int
    page_size: int

    @property
    def total_pages(self) -> int:
        if self.total == 0:
            return 0
        return math.ceil(self.total / self.page_size)


@dataclass(frozen=True, slots=True)
class ScanSummaryStats:
    """Aggregated scan intelligence metrics."""

    total_scans: int
    completed_scans: int
    failed_scans: int
    high_risk: int
    medium_risk: int
    low_risk: int
    average_risk_score: float


class ScanRepository:
    """Read-optimized queries for scan history and reporting."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_scans_paginated(self, *, page: int, page_size: int) -> PaginatedScanJobs:
        """Return scan jobs sorted by newest first with total count."""
        total = await self._session.scalar(select(func.count()).select_from(ScanJob)) or 0
        offset = (page - 1) * page_size

        result = await self._session.execute(
            select(ScanJob)
            .options(selectinload(ScanJob.result))
            .order_by(ScanJob.created_at.desc(), ScanJob.id.desc())
            .offset(offset)
            .limit(page_size)
        )

        return PaginatedScanJobs(
            items=list(result.scalars().all()),
            total=total,
            page=page,
            page_size=page_size,
        )

    async def get_summary_stats(self) -> ScanSummaryStats:
        """Aggregate scan counts and risk distribution for dashboard reporting."""
        total_scans = await self._session.scalar(select(func.count()).select_from(ScanJob)) or 0
        completed_scans = (
            await self._session.scalar(
                select(func.count())
                .select_from(ScanJob)
                .where(ScanJob.status == ScanJobStatus.COMPLETED)
            )
            or 0
        )
        failed_scans = (
            await self._session.scalar(
                select(func.count())
                .select_from(ScanJob)
                .where(ScanJob.status == ScanJobStatus.FAILED)
            )
            or 0
        )

        high_risk = await self._count_completed_by_risk_level(RiskLevel.HIGH)
        medium_risk = await self._count_completed_by_risk_level(RiskLevel.MEDIUM)
        low_risk = await self._count_completed_by_risk_level(RiskLevel.LOW)

        average_raw = await self._session.scalar(
            select(func.avg(ScanJob.risk_score)).where(
                ScanJob.status == ScanJobStatus.COMPLETED,
                ScanJob.risk_score.is_not(None),
            )
        )
        average_risk_score = _round_average(average_raw)

        return ScanSummaryStats(
            total_scans=total_scans,
            completed_scans=completed_scans,
            failed_scans=failed_scans,
            high_risk=high_risk,
            medium_risk=medium_risk,
            low_risk=low_risk,
            average_risk_score=average_risk_score,
        )

    async def _count_completed_by_risk_level(self, risk_level: RiskLevel) -> int:
        count = await self._session.scalar(
            select(func.count())
            .select_from(ScanResult)
            .join(ScanJob, ScanResult.scan_job_id == ScanJob.id)
            .where(
                ScanJob.status == ScanJobStatus.COMPLETED,
                ScanResult.risk_level == risk_level,
            )
        )
        return count or 0


def _round_average(value: Decimal | float | None) -> float:
    if value is None:
        return 0.0
    return round(float(value), 1)
