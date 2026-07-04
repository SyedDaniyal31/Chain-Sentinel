"""M5.0 chains API tests."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_chains_returns_supported_catalog(client: AsyncClient) -> None:
    response = await client.get("/api/v1/chains")

    assert response.status_code == 200
    data = response.json()
    assert len(data["chains"]) == 6

    mainnet = next(chain for chain in data["chains"] if chain["chain_id"] == 1)
    assert mainnet == {
        "chain_id": 1,
        "name": "Ethereum Mainnet",
        "native_currency": "ETH",
        "explorer_url": "https://etherscan.io",
        "testnet": False,
        "supported": True,
    }


@pytest.mark.asyncio
async def test_create_scan_rejects_unsupported_chain(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/scans",
        json={
            "scan_type": "wallet",
            "target_address": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0",
            "chain_id": 999,
        },
    )

    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "unsupported_chain"
    assert "999" in body["detail"]


@pytest.mark.asyncio
async def test_create_scan_defaults_to_mainnet_chain_id(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/scans",
        json={
            "scan_type": "wallet",
            "target_address": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0",
        },
    )

    assert response.status_code == 201
    scan_id = response.json()["id"]
    detail = await client.get(f"/api/v1/scans/{scan_id}")
    assert detail.status_code == 200
    assert detail.json()["chain_id"] == 1
