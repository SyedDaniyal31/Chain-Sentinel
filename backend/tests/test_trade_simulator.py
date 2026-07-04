"""TradeSimulator unit tests with mocked Anvil RPC."""

from unittest.mock import AsyncMock

import pytest

from app.blockchain.anvil_client import AnvilForkConfig
from app.models.enums import HoneypotSimulationStatus
from app.blockchain.trade_simulator import TradeSimulator


@pytest.fixture
def mock_anvil() -> AsyncMock:
    client = AsyncMock()
    client.reset_fork = AsyncMock()
    client.set_balance = AsyncMock()
    client.impersonate_account = AsyncMock()
    client.stop_impersonating_account = AsyncMock()
    client.wait_for_transaction = AsyncMock(return_value=True)
    client.get_balance = AsyncMock(return_value=0)
    return client


@pytest.mark.asyncio
async def test_trade_simulator_reports_no_pair(mock_anvil: AsyncMock) -> None:
    mock_anvil.eth_call = AsyncMock(return_value=b"\x00" * 32)
    simulator = TradeSimulator(mock_anvil, eth_amount_wei=10**17)

    result = await simulator.simulate(
        "0x742d35cc6634c0532925a3b844bc9e7595f0beb0",
        1,
        fork_config=AnvilForkConfig(
            fork_rpc_url="https://eth.example",
            chain_id=1,
        ),
    )

    assert result.simulated is True
    assert result.can_buy is False
    assert result.can_sell is False
    assert result.simulation is not None
    assert result.simulation.status == HoneypotSimulationStatus.SKIPPED


@pytest.mark.asyncio
async def test_trade_simulator_measures_buy_and_sell_taxes(mock_anvil: AsyncMock) -> None:
    pair = bytes.fromhex("000000000000000000000000" + "a0b86991c6218b36c1d19d4a2e9eb0ce3606eb48")
    token = "0x742d35cc6634c0532925a3b844bc9e7595f0beb0"
    router = "0x7a250d5630b4cf539739df2c5dacb4c659f2488d"
    factory = "0x5c69bee701ef814a2b6a3edd4b1652cb9cc5aa6f"

    buy_quote = (
        (32).to_bytes(32, byteorder="big")
        + (2).to_bytes(32, byteorder="big")
        + (10**17).to_bytes(32, byteorder="big")
        + (1_000_000).to_bytes(32, byteorder="big")
    )
    sell_quote = (
        (32).to_bytes(32, byteorder="big")
        + (2).to_bytes(32, byteorder="big")
        + (750_000).to_bytes(32, byteorder="big")
        + (8 * 10**16).to_bytes(32, byteorder="big")
    )

    balance_sequence = iter(
        [
            750_000,  # post-buy buyer balance (25% buy tax)
            750_000,  # pre-transfer
            562_500,  # post-transfer sellable remainder
            562_500,  # pre-sell balance
        ]
    )
    eth_balances = iter([10**18, 10**18 + 4 * 10**16])  # 50% sell tax on quoted ETH
    quote_responses = iter([buy_quote, sell_quote])

    async def eth_call(transaction: dict[str, str]) -> bytes:
        to = transaction["to"].lower()
        data = transaction["data"]
        if to == factory.lower() and data.startswith("0xe6a43905"):
            return pair
        if to == router.lower() and data.startswith("0xd06ca61f"):
            return next(quote_responses)
        if to == token.lower() and data.startswith("0x70a08231"):
            return next(balance_sequence).to_bytes(32, byteorder="big")
        return b"\x00" * 32

    mock_anvil.eth_call = eth_call
    mock_anvil.get_balance = AsyncMock(side_effect=lambda _addr: next(eth_balances))
    mock_anvil.eth_send_transaction = AsyncMock(return_value="0xdeadbeef")

    simulator = TradeSimulator(mock_anvil, eth_amount_wei=10**17)
    result = await simulator.simulate(
        token,
        1,
        fork_config=AnvilForkConfig(fork_rpc_url="https://eth.example", chain_id=1),
    )

    assert result.simulated is True
    assert result.can_buy is True
    assert result.can_sell is True
    assert result.buy_tax_bps == 2500
    assert result.sell_tax_bps == 5000
    assert result.simulation is not None
    assert result.simulation.buy.success is True
    assert result.simulation.transfer.success is True
    assert result.simulation.sell.success is True


@pytest.mark.asyncio
async def test_trade_simulator_detects_transfer_restriction(mock_anvil: AsyncMock) -> None:
    pair = bytes.fromhex("000000000000000000000000" + "a0b86991c6218b36c1d19d4a2e9eb0ce3606eb48")
    token = "0x742d35cc6634c0532925a3b844bc9e7595f0beb0"
    router = "0x7a250d5630b4cf539739df2c5dacb4c659f2488d"
    factory = "0x5c69bee701ef814a2b6a3edd4b1652cb9cc5aa6f"
    buy_quote = (
        (32).to_bytes(32, byteorder="big")
        + (2).to_bytes(32, byteorder="big")
        + (10**17).to_bytes(32, byteorder="big")
        + (1_000_000).to_bytes(32, byteorder="big")
    )

    async def eth_call(transaction: dict[str, str]) -> bytes:
        to = transaction["to"].lower()
        data = transaction["data"]
        if to == factory.lower():
            return pair
        if to == router.lower():
            return buy_quote
        if to == token.lower() and data.startswith("0x70a08231"):
            return (1_000_000).to_bytes(32, byteorder="big")
        return b"\x00" * 32

    mock_anvil.eth_call = eth_call
    mock_anvil.eth_send_transaction = AsyncMock(return_value="0xabc")
    mock_anvil.wait_for_transaction = AsyncMock(side_effect=[True, False])

    simulator = TradeSimulator(mock_anvil, eth_amount_wei=10**17)
    result = await simulator.simulate(
        token,
        1,
        fork_config=AnvilForkConfig(fork_rpc_url="https://eth.example", chain_id=1),
    )

    assert result.can_buy is True
    assert result.can_sell is False
