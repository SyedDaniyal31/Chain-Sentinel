"""CapabilityAnalyzer unit tests."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from hexbytes import HexBytes

from app.blockchain.capability import MINT_SELECTORS, PAUSE_SELECTORS
from app.blockchain.source_verification import VerifiedContractSource
from app.models.enums import CapabilityDetectionMethod
from app.schemas.scan_result import CapabilityAnalysisData
from app.services.capability_analyzer import CapabilityAnalyzer

TOKEN = "0x742d35cc6634c0532925a3b844bc9e7595f0beb0"


class FakeSourceProvider:
    def __init__(self, verified: VerifiedContractSource | None) -> None:
        self._verified = verified
        self.calls: list[tuple[str, int]] = []

    async def get_verified_source(
        self,
        contract_address: str,
        chain_id: int,
    ) -> VerifiedContractSource | None:
        self.calls.append((contract_address.lower(), chain_id))
        return self._verified


def _build_mock_web3(*, bytecode: bytes = b"") -> MagicMock:
    class MockEth:
        async def get_code(self, _address: str) -> HexBytes:
            return HexBytes(bytecode)

    web3 = MagicMock()
    web3.eth = MockEth()
    return web3


@pytest.mark.asyncio
async def test_capability_analyzer_uses_bytecode_when_source_unavailable() -> None:
    mint_selector = next(iter(MINT_SELECTORS))
    pause_selector = next(iter(PAUSE_SELECTORS))
    bytecode = b"\x60\x80" + mint_selector + pause_selector

    analyzer = CapabilityAnalyzer(
        _build_mock_web3(bytecode=bytecode),
        chain_id=11155111,
        source_provider=FakeSourceProvider(None),
    )

    result = await analyzer.analyze(TOKEN, bytecode=bytecode)

    assert result.mint_capability is True
    assert result.pause_capability is True
    assert result.blacklist_capability is False
    assert result.ownership_capability is False
    assert result.detection_method == CapabilityDetectionMethod.BYTECODE
    assert result.capability_count >= 2
    assert result.capabilities["mint"].enabled is True
    assert result.capabilities["mint"].controller == "unknown"


@pytest.mark.asyncio
async def test_capability_analyzer_prefers_verified_abi() -> None:
    verified = VerifiedContractSource(
        contract_name="TestToken",
        source_code="contract TestToken {}",
        abi=[
            {"type": "function", "name": "mint", "inputs": []},
            {"type": "function", "name": "owner", "inputs": []},
        ],
    )
    provider = FakeSourceProvider(verified)
    analyzer = CapabilityAnalyzer(
        _build_mock_web3(bytecode=b""),
        chain_id=11155111,
        source_provider=provider,
    )

    result = await analyzer.analyze(TOKEN, bytecode=b"\x60\x80")

    assert result.mint_capability is True
    assert result.ownership_capability is True
    assert result.detection_method == CapabilityDetectionMethod.SOURCE
    assert provider.calls == [(TOKEN, 11155111)]


@pytest.mark.asyncio
async def test_capability_analyzer_targets_implementation_bytecode() -> None:
    impl = "0xdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef"
    mint_selector = next(iter(MINT_SELECTORS))
    impl_bytecode = b"\x60\x80" + mint_selector
    proxy_bytecode = b"\x60\x80\x60\x40"

    web3 = _build_mock_web3(bytecode=proxy_bytecode)
    analyzer = CapabilityAnalyzer(
        web3,
        chain_id=11155111,
        source_provider=FakeSourceProvider(None),
    )

    result = await analyzer.analyze(
        TOKEN,
        bytecode=proxy_bytecode,
        implementation_address=impl,
        implementation_bytecode=impl_bytecode,
    )

    assert result.mint_capability is True
    assert result.detection_method == CapabilityDetectionMethod.BYTECODE


@pytest.mark.asyncio
async def test_capability_analyzer_fetches_implementation_code_when_missing() -> None:
    impl = "0xdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef"
    mint_selector = next(iter(MINT_SELECTORS))
    impl_bytecode = b"\x60\x80" + mint_selector

    web3 = _build_mock_web3(bytecode=impl_bytecode)
    web3.eth.get_code = AsyncMock(return_value=HexBytes(impl_bytecode))

    analyzer = CapabilityAnalyzer(
        web3,
        chain_id=11155111,
        source_provider=FakeSourceProvider(None),
    )

    result = await analyzer.analyze(
        TOKEN,
        bytecode=b"\x60\x80",
        implementation_address=impl,
    )

    assert result.mint_capability is True
    web3.eth.get_code.assert_awaited_once()
