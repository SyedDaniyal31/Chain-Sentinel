"""Scan history and summary API tests."""

import pytest
from httpx import AsyncClient

VALID_ADDRESS = "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0"
UNI_V3_FACTORY = "0x1f9840a85d5af5bf1d1762f925bdaddc4201f984"


@pytest.mark.asyncio
async def test_list_scans_empty(client: AsyncClient) -> None:
    response = await client.get("/api/v1/scans")

    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["total"] == 0
    assert data["page"] == 1
    assert data["page_size"] == 20
    assert data["total_pages"] == 0


@pytest.mark.asyncio
async def test_list_scans_returns_completed_jobs(client: AsyncClient) -> None:
    await client.post(
        "/api/v1/scans",
        json={"scan_type": "wallet", "target_address": VALID_ADDRESS, "chain_id": 11155111},
    )
    await client.post(
        "/api/v1/scans",
        json={"scan_type": "contract", "target_address": UNI_V3_FACTORY, "chain_id": 11155111},
    )

    response = await client.get("/api/v1/scans?page=1&page_size=10")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2
    assert data["page"] == 1
    assert data["page_size"] == 10
    assert data["total_pages"] == 1

    newest = data["items"][0]
    assert newest["scan_type"] == "contract"
    assert newest["status"] == "completed"
    assert newest["target_address"] == UNI_V3_FACTORY.lower()
    assert "created_at" in newest


@pytest.mark.asyncio
async def test_list_scans_sorted_newest_first(client: AsyncClient) -> None:
    first = await client.post(
        "/api/v1/scans",
        json={"scan_type": "wallet", "target_address": VALID_ADDRESS, "chain_id": 11155111},
    )
    second = await client.post(
        "/api/v1/scans",
        json={"scan_type": "contract", "target_address": UNI_V3_FACTORY, "chain_id": 11155111},
    )

    response = await client.get("/api/v1/scans")
    items = response.json()["items"]

    assert items[0]["id"] == second.json()["id"]
    assert items[1]["id"] == first.json()["id"]


@pytest.mark.asyncio
async def test_list_scans_pagination(client: AsyncClient) -> None:
    for index in range(3):
        await client.post(
            "/api/v1/scans",
            json={"scan_type": "wallet", "target_address": VALID_ADDRESS, "chain_id": 11155111},
        )

    page_one = await client.get("/api/v1/scans?page=1&page_size=2")
    page_two = await client.get("/api/v1/scans?page=2&page_size=2")

    assert page_one.status_code == 200
    assert page_two.status_code == 200
    assert len(page_one.json()["items"]) == 2
    assert len(page_two.json()["items"]) == 1
    assert page_one.json()["total_pages"] == 2


@pytest.mark.asyncio
async def test_list_scans_rejects_invalid_page(client: AsyncClient) -> None:
    response = await client.get("/api/v1/scans?page=0")

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_list_scans_rejects_invalid_page_size(client: AsyncClient) -> None:
    response = await client.get("/api/v1/scans?page_size=101")

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_scan_summary_empty(client: AsyncClient) -> None:
    response = await client.get("/api/v1/scans/summary")

    assert response.status_code == 200
    data = response.json()
    assert data == {
        "total_scans": 0,
        "completed_scans": 0,
        "failed_scans": 0,
        "high_risk": 0,
        "medium_risk": 0,
        "low_risk": 0,
        "average_risk_score": 0.0,
    }


@pytest.mark.asyncio
async def test_get_scan_summary_after_scans(client: AsyncClient) -> None:
    await client.post(
        "/api/v1/scans",
        json={"scan_type": "wallet", "target_address": VALID_ADDRESS, "chain_id": 11155111},
    )
    await client.post(
        "/api/v1/scans",
        json={"scan_type": "contract", "target_address": UNI_V3_FACTORY, "chain_id": 11155111},
    )

    response = await client.get("/api/v1/scans/summary")

    assert response.status_code == 200
    data = response.json()
    assert data["total_scans"] == 2
    assert data["completed_scans"] == 2
    assert data["failed_scans"] == 0
    assert data["low_risk"] == 1
    assert data["average_risk_score"] > 0.0


@pytest.mark.asyncio
async def test_scan_summary_route_not_shadowed_by_scan_id(client: AsyncClient) -> None:
    response = await client.get("/api/v1/scans/summary")

    assert response.status_code == 200
    assert "total_scans" in response.json()
