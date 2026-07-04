"""M4.2 EtherscanSourceProvider unit tests."""

import json
from unittest.mock import AsyncMock, patch

import pytest

from app.blockchain.contract_source_provider import ContractMetadata
from app.blockchain.etherscan_source_provider import EtherscanSourceProvider


@pytest.fixture
def provider() -> EtherscanSourceProvider:
    return EtherscanSourceProvider("test-api-key", timeout_seconds=5)


@pytest.mark.asyncio
async def test_etherscan_provider_parses_verified_source(provider: EtherscanSourceProvider) -> None:
    payload = {
        "status": "1",
        "result": [
            {
                "SourceCode": "contract Token {}",
                "ABI": json.dumps([{"type": "function", "name": "mint", "inputs": []}]),
                "ContractName": "Token",
                "CompilerVersion": "v0.8.20+commit.a1b79de6",
                "OptimizationUsed": "1",
                "Runs": "200",
                "EVMVersion": "paris",
                "LicenseType": "MIT",
                "Proxy": "0",
            }
        ],
    }

    with patch("httpx.AsyncClient") as client_cls:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=_mock_response(payload))
        client_cls.return_value.__aenter__.return_value = mock_client
        verified = await provider.get_verified_source("0x742d35cc6634c0532925a3b844bc9e7595f0beb0", 1)

    assert verified is not None
    assert verified.contract_name == "Token"
    assert verified.compiler_version == "v0.8.20+commit.a1b79de6"
    assert verified.abi is not None
    assert verified.metadata is not None
    assert verified.metadata.optimization_enabled is True
    assert verified.metadata.optimization_runs == 200


@pytest.mark.asyncio
async def test_etherscan_provider_fetch_contract_metadata(provider: EtherscanSourceProvider) -> None:
    payload = {
        "status": "1",
        "result": [
            {
                "SourceCode": "contract X {}",
                "ABI": "[]",
                "ContractName": "X",
                "CompilerVersion": "v0.8.19",
                "Proxy": "1",
                "Implementation": "0x1111111111111111111111111111111111111111",
            }
        ],
    }

    with patch("httpx.AsyncClient") as client_cls:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=_mock_response(payload))
        client_cls.return_value.__aenter__.return_value = mock_client
        metadata = await provider.fetch_contract_metadata(
            "0x742d35cc6634c0532925a3b844bc9e7595f0beb0",
            1,
        )

    assert isinstance(metadata, ContractMetadata)
    assert metadata.is_proxy is True
    assert metadata.implementation_address == "0x1111111111111111111111111111111111111111"


@pytest.mark.asyncio
async def test_etherscan_provider_returns_none_when_unverified(provider: EtherscanSourceProvider) -> None:
    payload = {"status": "0", "result": "Contract source code not verified"}

    with patch("httpx.AsyncClient") as client_cls:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=_mock_response(payload))
        client_cls.return_value.__aenter__.return_value = mock_client
        verified = await provider.get_verified_source("0x742d35cc6634c0532925a3b844bc9e7595f0beb0", 1)

    assert verified is None


class _MockResponse:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self._payload


def _mock_response(payload: dict) -> _MockResponse:
    return _MockResponse(payload)
