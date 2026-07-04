"""M4.1 honeypot trade simulation integration tests with mocked Anvil."""

from unittest.mock import AsyncMock, patch

import pytest

from app.blockchain.anvil_client import AnvilForkConfig
from app.blockchain.honeypot_simulation import HoneypotSimulationResult
from app.blockchain.trade_simulator import TradeSimulator
from app.models.enums import HoneypotFindingType, HoneypotSimulationStatus
from app.services.honeypot_analyzer import HoneypotAnalyzer
from tests.test_honeypot_analyzer import FakeSimulationProvider, FakeSourceProvider, TOKEN


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
async def test_trade_simulator_populates_three_phase_simulation_state(mock_anvil: AsyncMock) -> None:
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

    balance_sequence = iter([750_000, 750_000, 562_500, 562_500])
    eth_balances = iter([10**18, 10**18 + 4 * 10**16])
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
    assert result.simulation is not None
    assert result.simulation.status == HoneypotSimulationStatus.COMPLETED
    assert result.simulation.buy.attempted is True
    assert result.simulation.buy.success is True
    assert result.simulation.transfer.attempted is True
    assert result.simulation.transfer.success is True
    assert result.simulation.sell.attempted is True
    assert result.simulation.sell.success is True
    assert result.can_buy is True
    assert result.can_sell is True
    assert result.can_transfer is True


@pytest.mark.asyncio
async def test_trade_simulator_marks_transfer_path_blocked(mock_anvil: AsyncMock) -> None:
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

    assert result.simulation is not None
    assert result.simulation.transfer.attempted is True
    assert result.simulation.transfer.success is False
    assert result.can_transfer is False
    assert result.can_buy is True
    assert result.can_sell is False


@pytest.mark.asyncio
async def test_analyzer_generates_simulation_findings_from_provider() -> None:
    from tests.test_honeypot_analyzer import _build_mock_web3, _completed_simulation

    provider = FakeSimulationProvider(_completed_simulation(can_sell=False))
    analyzer = HoneypotAnalyzer(
        _build_mock_web3(bytecode=b""),
        chain_id=11155111,
        source_provider=FakeSourceProvider(None),
        simulation_provider=provider,
    )

    result = await analyzer.analyze(TOKEN, bytecode=b"\x60\x80")
    by_type = {finding.finding_type: finding for finding in result.findings}

    assert result.trade_simulated is True
    assert by_type[HoneypotFindingType.BUY_PATH_BLOCKED].enabled is False
    assert by_type[HoneypotFindingType.TRANSFER_PATH_BLOCKED].enabled is False
    assert by_type[HoneypotFindingType.SELL_PATH_BLOCKED].enabled is True
    assert by_type[HoneypotFindingType.HONEYPOT_CONFIRMED].enabled is True
    assert result.summary.is_confirmed is True


@pytest.mark.asyncio
async def test_anvil_provider_delegates_to_trade_simulator() -> None:
    from app.blockchain.anvil_honeypot_simulation import AnvilHoneypotSimulationProvider

    completed = HoneypotSimulationResult(
        can_buy=True,
        can_sell=False,
        simulated=True,
    )
    provider = AnvilHoneypotSimulationProvider(
        anvil_rpc_url="http://127.0.0.1:8545",
        fork_rpc_url="https://eth.example",
        chain_id=1,
    )

    with patch.object(provider, "_resolve_rpc_url", AsyncMock(return_value="http://127.0.0.1:8545")):
        with patch(
            "app.blockchain.anvil_honeypot_simulation.TradeSimulator.simulate",
            AsyncMock(return_value=completed),
        ) as simulate_mock:
            result = await provider.simulate_trade_paths(TOKEN, 1)

    assert result is completed
    simulate_mock.assert_awaited_once()
