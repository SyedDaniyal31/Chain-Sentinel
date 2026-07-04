"""Scan job API tests."""

import pytest
from httpx import AsyncClient

from app.models.enums import ScanType
from app.services.risk_score import compute_mock_risk_score

VALID_ADDRESS = "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0"
UNI_V3_FACTORY = "0x1f9840a85d5af5bf1d1762f925bdaddc4201f984"


@pytest.mark.asyncio
async def test_create_scan_returns_201(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/scans",
        json={"scan_type": "wallet", "target_address": VALID_ADDRESS, "chain_id": 11155111},
    )

    assert response.status_code == 201


@pytest.mark.asyncio
async def test_create_scan_response_body(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/scans",
        json={"scan_type": "wallet", "target_address": VALID_ADDRESS, "chain_id": 11155111},
    )

    data = response.json()
    assert data["id"] >= 1
    assert data["status"] == "pending"


@pytest.mark.asyncio
async def test_create_scan_rejects_invalid_address(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/scans",
        json={"scan_type": "wallet", "target_address": "0x123", "chain_id": 11155111},
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_scan_rejects_invalid_scan_type(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/scans",
        json={"scan_type": "invalid", "target_address": VALID_ADDRESS},
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_scan_returns_full_job(client: AsyncClient) -> None:
    create_response = await client.post(
        "/api/v1/scans",
        json={"scan_type": "wallet", "target_address": VALID_ADDRESS, "chain_id": 11155111},
    )
    scan_id = create_response.json()["id"]

    response = await client.get(f"/api/v1/scans/{scan_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == scan_id
    assert data["scan_type"] == "wallet"
    assert data["target_address"] == VALID_ADDRESS.lower()
    assert data["status"] in {"pending", "running", "completed"}
    assert "created_at" in data
    assert "updated_at" in data


@pytest.mark.asyncio
async def test_scan_lifecycle_completes_via_background_worker(client: AsyncClient) -> None:
    create_response = await client.post(
        "/api/v1/scans",
        json={"scan_type": "wallet", "target_address": VALID_ADDRESS, "chain_id": 11155111},
    )
    assert create_response.status_code == 201
    assert create_response.json()["status"] == "pending"

    scan_id = create_response.json()["id"]
    get_response = await client.get(f"/api/v1/scans/{scan_id}")

    assert get_response.status_code == 200
    data = get_response.json()
    assert data["status"] == "completed"
    assert data["risk_score"] is not None
    expected_score = compute_mock_risk_score(ScanType.WALLET, VALID_ADDRESS.lower())
    assert float(data["risk_score"]) == float(expected_score)
    assert data["result"] is not None
    assert data["result"]["chain_id"] == 11155111
    assert data["result"]["latest_block"] == 12345678
    assert data["result"]["wallet_balance_wei"] == 1000000000000000000
    assert data["result"]["wallet_balance_eth"] == "1"


@pytest.mark.asyncio
async def test_contract_scan_lifecycle_completes_via_background_worker(client: AsyncClient) -> None:
    create_response = await client.post(
        "/api/v1/scans",
        json={"scan_type": "contract", "target_address": UNI_V3_FACTORY, "chain_id": 11155111},
    )
    assert create_response.status_code == 201

    scan_id = create_response.json()["id"]
    get_response = await client.get(f"/api/v1/scans/{scan_id}")

    assert get_response.status_code == 200
    data = get_response.json()
    assert data["scan_type"] == "contract"
    assert data["status"] == "completed"
    assert data["result"] is not None
    assert data["result"]["is_contract"] is True
    assert data["result"]["bytecode_size"] == 24576
    assert data["result"]["is_upgradeable"] is False
    assert data["result"]["implementation_address"] is None
    assert data["result"]["admin_address"] is None
    assert data["result"]["wallet_balance_wei"] is None
    assert data["result"]["wallet_balance_eth"] is None
    assert float(data["risk_score"]) == 0.0
    assert data["result"]["risk_level"] == "low"
    assert data["result"]["risk_reasons"] == ["No upgradeability indicators detected"]


@pytest.mark.asyncio
async def test_get_scan_not_found(client: AsyncClient) -> None:
    response = await client.get("/api/v1/scans/99999")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_get_scan_rejects_invalid_id(client: AsyncClient) -> None:
    response = await client.get("/api/v1/scans/0")

    assert response.status_code == 422
