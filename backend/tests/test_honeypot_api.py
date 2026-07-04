"""M4 honeypot intelligence API tests."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_scan_includes_honeypot_object(client: AsyncClient) -> None:
    create_response = await client.post(
        "/api/v1/scans",
        json={"scan_type": "contract", "target_address": "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2", "chain_id": 11155111},
    )
    scan_id = create_response.json()["id"]
    response = await client.get(f"/api/v1/scans/{scan_id}")

    assert response.status_code == 200
    result = response.json()["result"]
    assert "honeypot" in result
    assert "summary" in result["honeypot"]
    assert "findings" in result["honeypot"]
    assert "simulation" in result["honeypot"]
    assert result["honeypot"]["simulation"]["status"] == "not_run"
    assert isinstance(result["honeypot"]["findings"], list)
    assert len(result["honeypot"]["findings"]) == 13
    assert result["honeypot_simulation_status"] == "not_run"
    assert result["trading_enabled_control"] is False


@pytest.mark.asyncio
async def test_get_scan_honeypot_legacy_fields_preserved(client: AsyncClient) -> None:
    create_response = await client.post(
        "/api/v1/scans",
        json={"scan_type": "contract", "target_address": "0x742d35cc6634c0532925a3b844bc9e7595f0beb0", "chain_id": 11155111},
    )
    scan_id = create_response.json()["id"]
    result = (await client.get(f"/api/v1/scans/{scan_id}")).json()["result"]

    for field in (
        "trading_enabled_control",
        "whitelist_control",
        "blacklist_sell_blocking",
        "transfer_tax_control",
        "can_buy",
        "can_sell",
        "trade_simulated",
    ):
        assert field in result
