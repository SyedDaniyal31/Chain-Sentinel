"""HoneypotAnalyzer unit tests."""

from unittest.mock import MagicMock

import pytest
from hexbytes import HexBytes

from app.blockchain.honeypot import TRADING_ENABLED_SELECTORS, TRANSFER_TAX_SELECTORS
from app.blockchain.honeypot_simulation import (
    HoneypotSimulationProvider,
    HoneypotSimulationResult,
)
from app.blockchain.honeypot_simulation_state import (
    HoneypotSimulationState,
    HoneypotTradePathResult,
)
from app.blockchain.source_verification import VerifiedContractSource
from app.models.enums import (
    HoneypotDetectionMethod,
    HoneypotFindingType,
    HoneypotSimulationStatus,
)
from app.services.honeypot_analyzer import HoneypotAnalyzer

TOKEN = "0x742d35cc6634c0532925a3b844bc9e7595f0beb0"


class FakeSourceProvider:
    def __init__(self, verified: VerifiedContractSource | None) -> None:
        self._verified = verified

    async def get_verified_source(
        self,
        contract_address: str,
        chain_id: int,
    ) -> VerifiedContractSource | None:
        return self._verified


class FakeSimulationProvider(HoneypotSimulationProvider):
    def __init__(self, result: HoneypotSimulationResult | None) -> None:
        self._result = result
        self.calls: list[tuple[str, int]] = []

    async def simulate_trade_paths(
        self,
        token_address: str,
        chain_id: int,
        *,
        pair_address: str | None = None,
    ) -> HoneypotSimulationResult | None:
        self.calls.append((token_address.lower(), chain_id))
        return self._result


def _completed_simulation(*, can_sell: bool) -> HoneypotSimulationResult:
    return HoneypotSimulationResult(
        can_buy=True,
        can_sell=can_sell,
        can_transfer=True,
        buy_tax_bps=300,
        sell_tax_bps=9900 if not can_sell else 300,
        simulated=True,
        simulation=HoneypotSimulationState(
            status=HoneypotSimulationStatus.COMPLETED,
            pair_address="0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48",
            router_address="0x7a250d5630b4cf539739df2c5dacb4c659f2488d",
            buy=HoneypotTradePathResult(attempted=True, success=True, tax_bps=300),
            transfer=HoneypotTradePathResult(attempted=True, success=True),
            sell=HoneypotTradePathResult(
                attempted=True,
                success=can_sell,
                tax_bps=9900 if not can_sell else 300,
                revert_reason=None if can_sell else "SWAP_TOKENS_FOR_ETH_FAILED",
            ),
            round_trip_success=can_sell,
        ),
    )


def _build_mock_web3(*, bytecode: bytes = b"") -> MagicMock:
    class MockEth:
        async def get_code(self, _address: str) -> HexBytes:
            return HexBytes(bytecode)

    web3 = MagicMock()
    web3.eth = MockEth()
    return web3


@pytest.mark.asyncio
async def test_honeypot_analyzer_uses_bytecode_when_source_unavailable() -> None:
    trading_selector = next(iter(TRADING_ENABLED_SELECTORS))
    tax_selector = next(iter(TRANSFER_TAX_SELECTORS))
    bytecode = b"\x60\x80" + trading_selector + tax_selector

    analyzer = HoneypotAnalyzer(
        _build_mock_web3(bytecode=bytecode),
        chain_id=11155111,
        source_provider=FakeSourceProvider(None),
    )

    result = await analyzer.analyze(TOKEN, bytecode=bytecode)

    assert result.trading_enabled_control is True
    assert result.transfer_tax_control is True
    assert result.detection_method == HoneypotDetectionMethod.BYTECODE
    assert result.simulation.status == HoneypotSimulationStatus.NOT_RUN
    assert result.trade_simulated is False
    assert result.can_sell is None
    assert len(result.findings) == 13
    assert result.summary.finding_count >= 2


@pytest.mark.asyncio
async def test_honeypot_analyzer_prefers_verified_abi() -> None:
    verified = VerifiedContractSource(
        contract_name="HoneypotToken",
        source_code="contract HoneypotToken {}",
        abi=[
            {"type": "function", "name": "enableTrading", "inputs": []},
            {"type": "function", "name": "isWhitelisted", "inputs": []},
        ],
    )
    analyzer = HoneypotAnalyzer(
        _build_mock_web3(bytecode=b""),
        chain_id=11155111,
        source_provider=FakeSourceProvider(verified),
    )

    result = await analyzer.analyze(TOKEN, bytecode=b"\x60\x80")

    assert result.trading_enabled_control is True
    assert result.whitelist_control is True
    assert result.detection_method == HoneypotDetectionMethod.SOURCE
    assert result.simulation.status == HoneypotSimulationStatus.NOT_RUN


@pytest.mark.asyncio
async def test_honeypot_analyzer_merges_simulation_results() -> None:
    simulation = FakeSimulationProvider(_completed_simulation(can_sell=False))
    analyzer = HoneypotAnalyzer(
        _build_mock_web3(bytecode=b""),
        chain_id=11155111,
        source_provider=FakeSourceProvider(None),
        simulation_provider=simulation,
    )

    result = await analyzer.analyze(TOKEN, bytecode=b"\x60\x80")

    assert result.blacklist_sell_blocking is True
    assert result.trade_simulated is True
    assert result.can_sell is False
    assert result.simulation.status == HoneypotSimulationStatus.COMPLETED
    assert result.simulation.sell.success is False
    assert result.summary.is_confirmed is True
    assert result.summary.honeypot_score >= 90
    assert result.detection_method == HoneypotDetectionMethod.SIMULATION
    assert simulation.calls == [(TOKEN, 11155111)]

    by_type = {finding.finding_type: finding for finding in result.findings}
    assert by_type[HoneypotFindingType.SELL_PATH_BLOCKED].enabled is True
    assert by_type[HoneypotFindingType.HONEYPOT_CONFIRMED].enabled is True
    assert by_type[HoneypotFindingType.HIGH_SELL_TAX].enabled is True


@pytest.mark.asyncio
async def test_honeypot_analyzer_targets_implementation_bytecode() -> None:
    impl = "0xdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef"
    trading_selector = next(iter(TRADING_ENABLED_SELECTORS))
    impl_bytecode = b"\x60\x80" + trading_selector

    analyzer = HoneypotAnalyzer(
        _build_mock_web3(bytecode=impl_bytecode),
        chain_id=11155111,
        source_provider=FakeSourceProvider(None),
    )

    result = await analyzer.analyze(
        TOKEN,
        bytecode=b"\x60\x80",
        implementation_address=impl,
        implementation_bytecode=impl_bytecode,
    )

    assert result.trading_enabled_control is True
