"""WalletAnalyzer and address validation tests."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.exceptions import BlockchainRpcError
from app.core.validators import is_valid_eth_address, normalize_eth_address
from app.schemas.scan_result import WalletAnalysisData
from app.services.wallet_analyzer import WalletAnalyzer

VALID_ADDRESS = "0x742d35cc6634c0532925a3b844bc9e7595f0beb0"


def test_normalize_eth_address_lowercases() -> None:
    assert normalize_eth_address(VALID_ADDRESS.upper()) == VALID_ADDRESS


def test_normalize_eth_address_rejects_invalid() -> None:
    with pytest.raises(ValueError, match="valid 20-byte EVM address"):
        normalize_eth_address("0x123")


def test_is_valid_eth_address() -> None:
    assert is_valid_eth_address(VALID_ADDRESS) is True
    assert is_valid_eth_address("not-an-address") is False


def _build_mock_web3(
    *,
    connected: bool = True,
    chain_id: int = 11155111,
    block_number: int = 12345678,
    balance_wei: int = 1000000000000000000,
) -> MagicMock:
    class MockEth:
        async def get_balance(self, _address: str) -> int:
            return balance_wei

        @property
        async def chain_id(self) -> int:
            return chain_id

        @property
        async def block_number(self) -> int:
            return block_number

    web3 = MagicMock()
    web3.is_connected = AsyncMock(return_value=connected)
    web3.eth = MockEth()
    return web3


@pytest.mark.asyncio
async def test_wallet_analyzer_returns_chain_data() -> None:
    analyzer = WalletAnalyzer(_build_mock_web3())

    result = await analyzer.analyze(VALID_ADDRESS)

    assert result == WalletAnalysisData(
        chain_id=11155111,
        latest_block=12345678,
        wallet_balance_wei=1000000000000000000,
    )


@pytest.mark.asyncio
async def test_wallet_analyzer_raises_when_not_connected() -> None:
    analyzer = WalletAnalyzer(_build_mock_web3(connected=False))

    with pytest.raises(BlockchainRpcError, match="Unable to connect"):
        await analyzer.analyze(VALID_ADDRESS)


@pytest.mark.asyncio
async def test_wallet_analyzer_raises_on_chain_id_mismatch() -> None:
    analyzer = WalletAnalyzer(_build_mock_web3(chain_id=1), expected_chain_id=11155111)

    with pytest.raises(BlockchainRpcError, match="does not match configured CHAIN_ID"):
        await analyzer.analyze(VALID_ADDRESS)


@pytest.mark.asyncio
async def test_wallet_analyzer_skips_chain_check_when_expected_is_none() -> None:
    analyzer = WalletAnalyzer(_build_mock_web3(chain_id=1), expected_chain_id=None)

    result = await analyzer.analyze(VALID_ADDRESS)

    assert result.chain_id == 1
