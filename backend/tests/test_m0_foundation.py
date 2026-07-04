"""M0 foundation hardening tests."""

import pytest
from httpx import AsyncClient

from app.core.analyzer_constants import ANALYZER_VERSION, resolve_scan_detection_method
from app.models.enums import (
    CapabilityDetectionMethod,
    HoneypotDetectionMethod,
    ScanDetectionMethod,
)

VALID_ADDRESS = "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0"
UNI_V3_FACTORY = "0x1f9840a85d5af5bf1d1762f925bdaddc4201f984"


def test_resolve_scan_detection_method_bytecode_only() -> None:
    result = resolve_scan_detection_method(
        CapabilityDetectionMethod.BYTECODE,
        HoneypotDetectionMethod.NONE,
    )
    assert result == ScanDetectionMethod.BYTECODE


def test_resolve_scan_detection_method_simulation_only() -> None:
    result = resolve_scan_detection_method(
        CapabilityDetectionMethod.NONE,
        HoneypotDetectionMethod.SIMULATION,
    )
    assert result == ScanDetectionMethod.SIMULATION


def test_resolve_scan_detection_method_hybrid_source_and_bytecode() -> None:
    result = resolve_scan_detection_method(
        CapabilityDetectionMethod.SOURCE,
        HoneypotDetectionMethod.BYTECODE,
    )
    assert result == ScanDetectionMethod.HYBRID


def test_resolve_scan_detection_method_hybrid_simulation_and_source() -> None:
    result = resolve_scan_detection_method(
        CapabilityDetectionMethod.SOURCE,
        HoneypotDetectionMethod.SIMULATION,
    )
    assert result == ScanDetectionMethod.HYBRID


def test_resolve_scan_detection_method_none_when_no_signals() -> None:
    result = resolve_scan_detection_method(
        CapabilityDetectionMethod.NONE,
        HoneypotDetectionMethod.NONE,
    )
    assert result is None


@pytest.mark.asyncio
async def test_get_scan_includes_m0_job_metadata(client: AsyncClient) -> None:
    create_response = await client.post(
        "/api/v1/scans",
        json={"scan_type": "contract", "target_address": UNI_V3_FACTORY, "chain_id": 11155111},
    )
    scan_id = create_response.json()["id"]

    response = await client.get(f"/api/v1/scans/{scan_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["chain_id"] == 11155111
    assert data["block_number"] == 12345678
    assert data["rpc_endpoint"] is not None
    assert len(data["rpc_endpoint"]) <= 255


@pytest.mark.asyncio
async def test_get_scan_includes_m0_result_metadata(client: AsyncClient) -> None:
    create_response = await client.post(
        "/api/v1/scans",
        json={"scan_type": "contract", "target_address": UNI_V3_FACTORY, "chain_id": 11155111},
    )
    scan_id = create_response.json()["id"]

    response = await client.get(f"/api/v1/scans/{scan_id}")

    assert response.status_code == 200
    result = response.json()["result"]
    assert result is not None
    assert result["analyzer_version"] == ANALYZER_VERSION
    assert result["detection_method"] == ScanDetectionMethod.BYTECODE.value


@pytest.mark.asyncio
async def test_wallet_scan_persists_analyzer_version(client: AsyncClient) -> None:
    create_response = await client.post(
        "/api/v1/scans",
        json={"scan_type": "wallet", "target_address": VALID_ADDRESS, "chain_id": 11155111},
    )
    scan_id = create_response.json()["id"]

    response = await client.get(f"/api/v1/scans/{scan_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["chain_id"] == 11155111
    assert data["block_number"] == 12345678
    assert data["result"]["analyzer_version"] == ANALYZER_VERSION
    assert data["result"]["detection_method"] is None


@pytest.mark.asyncio
async def test_create_scan_response_unchanged(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/scans",
        json={"scan_type": "wallet", "target_address": VALID_ADDRESS, "chain_id": 11155111},
    )

    assert response.status_code == 201
    data = response.json()
    assert set(data.keys()) == {"id", "status"}
