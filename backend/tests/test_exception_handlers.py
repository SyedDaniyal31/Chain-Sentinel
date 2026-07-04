"""Global exception handler tests."""

import pytest
from httpx import AsyncClient
from sqlalchemy.exc import ProgrammingError

from app.repositories import scan_repository


@pytest.mark.asyncio
async def test_validation_error_returns_structured_json(client: AsyncClient) -> None:
    response = await client.get("/api/v1/scans?page=0")

    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "validation_error"
    assert "page" in body["detail"].lower()


@pytest.mark.asyncio
async def test_database_schema_error_returns_503(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    async def failing_list(*_args, **_kwargs):
        raise ProgrammingError(
            "SELECT ...",
            {},
            Exception('column scan_jobs.chain_id does not exist'),
        )

    monkeypatch.setattr(scan_repository.ScanRepository, "list_scans_paginated", failing_list)

    response = await client.get("/api/v1/scans")

    assert response.status_code == 503
    body = response.json()
    assert body["error_code"] == "database_schema_error"
    assert "alembic upgrade head" in body["detail"].lower()


@pytest.mark.asyncio
async def test_scan_not_found_returns_404(client: AsyncClient) -> None:
    response = await client.get("/api/v1/scans/999999")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()
