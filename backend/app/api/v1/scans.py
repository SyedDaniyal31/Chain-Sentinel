"""Scan job API endpoints."""

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Path, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ScanNotFoundError
from app.db.session import get_db
from app.schemas.scan import (
    PaginatedScanListResponse,
    ScanCreateRequest,
    ScanCreateResponse,
    ScanJobResponse,
    ScanSummaryResponse,
)
from app.services.scan_service import ScanService
from app.services.scan_tasks import run_scan_worker

router = APIRouter()

MAX_PAGE_SIZE = 100
DEFAULT_PAGE_SIZE = 20


def get_scan_service(session: AsyncSession = Depends(get_db)) -> ScanService:
    return ScanService(session)


@router.get(
    "/scans/summary",
    response_model=ScanSummaryResponse,
    summary="Scan intelligence summary",
    description=(
        "Aggregate counts of total, completed, and failed scans plus risk band "
        "distribution and average risk score across completed jobs."
    ),
    responses={200: {"description": "Summary statistics computed successfully."}},
)
async def get_scan_summary(
    service: ScanService = Depends(get_scan_service),
) -> ScanSummaryResponse:
    return await service.get_scan_summary()


@router.get(
    "/scans",
    response_model=PaginatedScanListResponse,
    summary="List scan jobs",
    description=(
        "Return paginated scan history sorted by newest first. "
        "Use page and page_size query parameters to navigate large datasets."
    ),
    responses={
        200: {"description": "Paginated scan list returned."},
        422: {"description": "Invalid pagination parameters."},
    },
)
async def list_scans(
    page: Annotated[int, Query(ge=1, description="1-based page number.")] = 1,
    page_size: Annotated[
        int,
        Query(ge=1, le=MAX_PAGE_SIZE, description=f"Items per page (max {MAX_PAGE_SIZE})."),
    ] = DEFAULT_PAGE_SIZE,
    service: ScanService = Depends(get_scan_service),
) -> PaginatedScanListResponse:
    return await service.list_scans(page=page, page_size=page_size)


@router.post(
    "/scans",
    response_model=ScanCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create scan job",
    description=(
        "Queue a new wallet or contract analysis job. "
        "Processing runs asynchronously after the response is returned; "
        "poll GET /api/v1/scans/{id} for status, result, and risk_score updates."
    ),
    responses={
        201: {"description": "Scan job queued successfully."},
        422: {"description": "Validation error (invalid address, scan type, or chain_id)."},
    },
)
async def create_scan(
    payload: ScanCreateRequest,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_db),
    service: ScanService = Depends(get_scan_service),
) -> ScanCreateResponse:
    scan_job = await service.create_scan(
        payload.scan_type,
        payload.target_address,
        payload.chain_id,
    )
    # Commit before scheduling worker so the background session can read the row.
    await session.commit()
    background_tasks.add_task(run_scan_worker, scan_job.id)
    return ScanCreateResponse(id=scan_job.id, status=scan_job.status)


@router.get(
    "/scans/{scan_id}",
    response_model=ScanJobResponse,
    summary="Get scan job by ID",
    description=(
        "Retrieve the full persisted state of a scan job, including analyzer result and risk score. "
        "Status progresses pending → running → completed (or failed) as the background worker runs."
    ),
    responses={
        200: {"description": "Scan job found."},
        404: {"description": "Scan job not found."},
        422: {"description": "Invalid scan ID path parameter."},
    },
)
async def get_scan(
    scan_id: int = Path(..., ge=1, description="Unique scan job identifier."),
    service: ScanService = Depends(get_scan_service),
) -> ScanJobResponse:
    try:
        scan_job = await service.get_scan_by_id(scan_id)
    except ScanNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    return ScanJobResponse.model_validate(scan_job)
