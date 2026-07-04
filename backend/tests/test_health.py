"""Health check endpoint tests."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_health_returns_200(client: AsyncClient) -> None:
    response = await client.get("/health")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_health_response_body(client: AsyncClient) -> None:
    response = await client.get("/health")

    data = response.json()
    assert data == {
        "status": "healthy",
        "service": "ChainSentinel API",
        "version": "0.1.0",
    }
