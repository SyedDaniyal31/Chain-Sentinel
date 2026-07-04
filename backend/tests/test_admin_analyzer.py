"""EIP-1967 admin detection unit tests."""

from unittest.mock import MagicMock

import pytest
from hexbytes import HexBytes

from app.blockchain.eip1967 import EIP1967_ADMIN_SLOT, parse_eip1967_admin
from app.core.exceptions import BlockchainRpcError
from app.schemas.scan_result import AdminAnalysisData
from app.services.admin_analyzer import AdminAnalyzer

PROXY_ADDRESS = "0xa231aa3388416ebc1b8f8a51b412327832524ca4"
ADMIN_ADDRESS = "0x1234567890123456789012345678901234567890"


def _admin_storage_word(address: str) -> bytes:
    return b"\x00" * 12 + bytes.fromhex(address[2:])


def test_parse_eip1967_admin_returns_address() -> None:
    word = _admin_storage_word(ADMIN_ADDRESS)

    assert parse_eip1967_admin(word) == ADMIN_ADDRESS


def test_parse_eip1967_admin_returns_none_for_empty_slot() -> None:
    assert parse_eip1967_admin(b"\x00" * 32) is None


def _build_mock_web3(*, storage_word: bytes = b"\x00" * 32) -> MagicMock:
    class MockEth:
        async def get_storage_at(self, _address: str, slot: str) -> HexBytes:
            assert slot == EIP1967_ADMIN_SLOT
            return HexBytes(storage_word)

    web3 = MagicMock()
    web3.eth = MockEth()
    return web3


@pytest.mark.asyncio
async def test_admin_analyzer_detects_admin_address() -> None:
    analyzer = AdminAnalyzer(_build_mock_web3(storage_word=_admin_storage_word(ADMIN_ADDRESS)))

    result = await analyzer.analyze(PROXY_ADDRESS)

    assert result == AdminAnalysisData(admin_address=ADMIN_ADDRESS)


@pytest.mark.asyncio
async def test_admin_analyzer_returns_none_when_slot_empty() -> None:
    analyzer = AdminAnalyzer(_build_mock_web3())

    result = await analyzer.analyze(PROXY_ADDRESS)

    assert result == AdminAnalysisData(admin_address=None)


@pytest.mark.asyncio
async def test_admin_analyzer_raises_on_rpc_failure() -> None:
    web3 = MagicMock()

    async def fail(*_args: object, **_kwargs: object) -> HexBytes:
        raise ConnectionError("rpc down")

    web3.eth.get_storage_at = fail
    analyzer = AdminAnalyzer(web3)

    with pytest.raises(BlockchainRpcError, match="admin storage request failed"):
        await analyzer.analyze(PROXY_ADDRESS)
