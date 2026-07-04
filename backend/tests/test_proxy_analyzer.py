"""EIP-1967 proxy detection unit tests."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from hexbytes import HexBytes

from app.blockchain.eip1967 import EIP1967_IMPLEMENTATION_SLOT, parse_eip1967_implementation
from app.core.exceptions import BlockchainRpcError
from app.schemas.scan_result import ProxyAnalysisData
from app.services.proxy_analyzer import ProxyAnalyzer

PROXY_ADDRESS = "0xa231aa3388416ebc1b8f8a51b412327832524ca4"
IMPLEMENTATION_ADDRESS = "0xdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef"


def _implementation_storage_word(address: str) -> bytes:
    return b"\x00" * 12 + bytes.fromhex(address[2:])


def test_parse_eip1967_implementation_returns_address() -> None:
    word = _implementation_storage_word(IMPLEMENTATION_ADDRESS)

    assert parse_eip1967_implementation(word) == IMPLEMENTATION_ADDRESS


def test_parse_eip1967_implementation_returns_none_for_empty_slot() -> None:
    assert parse_eip1967_implementation(b"\x00" * 32) is None


def _build_mock_web3(*, storage_word: bytes = b"\x00" * 32) -> MagicMock:
    class MockEth:
        async def get_storage_at(self, _address: str, slot: str) -> HexBytes:
            assert slot == EIP1967_IMPLEMENTATION_SLOT
            return HexBytes(storage_word)

    web3 = MagicMock()
    web3.eth = MockEth()
    return web3


@pytest.mark.asyncio
async def test_proxy_analyzer_detects_upgradeable_contract() -> None:
    analyzer = ProxyAnalyzer(
        _build_mock_web3(storage_word=_implementation_storage_word(IMPLEMENTATION_ADDRESS))
    )

    result = await analyzer.analyze(PROXY_ADDRESS)

    assert result == ProxyAnalysisData(
        is_upgradeable=True,
        implementation_address=IMPLEMENTATION_ADDRESS,
    )


@pytest.mark.asyncio
async def test_proxy_analyzer_detects_non_upgradeable_contract() -> None:
    analyzer = ProxyAnalyzer(_build_mock_web3())

    result = await analyzer.analyze(PROXY_ADDRESS)

    assert result == ProxyAnalysisData(
        is_upgradeable=False,
        implementation_address=None,
    )


@pytest.mark.asyncio
async def test_proxy_analyzer_raises_on_rpc_failure() -> None:
    web3 = MagicMock()

    async def fail(*_args: object, **_kwargs: object) -> HexBytes:
        raise ConnectionError("rpc down")

    web3.eth.get_storage_at = fail
    analyzer = ProxyAnalyzer(web3)

    with pytest.raises(BlockchainRpcError, match="storage request failed"):
        await analyzer.analyze(PROXY_ADDRESS)
