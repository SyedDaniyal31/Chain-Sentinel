"""M3 capability intelligence API tests."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_scan_includes_capabilities_object(client: AsyncClient) -> None:
    create_response = await client.post(
        "/api/v1/scans",
        json={"scan_type": "contract", "target_address": "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2", "chain_id": 11155111},
    )
    scan_id = create_response.json()["id"]
    response = await client.get(f"/api/v1/scans/{scan_id}")

    assert response.status_code == 200
    result = response.json()["result"]
    assert "capabilities" in result
    assert isinstance(result["capabilities"], dict)
    assert "mint" in result["capabilities"]
    assert result["capability_count"] == 0
    assert result["capabilities"]["mint"]["enabled"] is False
    assert result["mint_capability"] is False
