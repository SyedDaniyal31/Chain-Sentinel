"""Honeypot and trading-restriction detection from verified source or bytecode."""

import logging

from web3 import AsyncWeb3

from app.blockchain.honeypot import (
    HoneypotFlags,
    _abi_function_names,
    merge_honeypot_flags,
)
from app.blockchain.honeypot_intelligence import (
    aggregate_detection_method,
    build_honeypot_findings,
    build_honeypot_summary,
    legacy_flags_from_findings,
    merge_source_into_honeypot_findings,
)
from app.blockchain.honeypot_simulation import (
    HoneypotSimulationProvider,
    HoneypotSimulationResult,
    NullHoneypotSimulationProvider,
)
from app.blockchain.honeypot_simulation_state import build_not_run_simulation_state
from app.blockchain.contract_source_provider import ContractSourceProvider, NullContractSourceProvider
from app.blockchain.source_analysis_engine import SourceAnalysisEngine, SourceAnalysisResult, merge_abi_function_names
from app.core.validators import normalize_eth_address
from app.models.enums import HoneypotDetectionMethod
from app.schemas.scan_result import HoneypotAnalysisData

logger = logging.getLogger(__name__)


class HoneypotAnalyzer:
    """
    Detect honeypot and trading-restriction patterns in token logic contracts.

    Priority:
        1. Anvil fork trade simulation (buy → transfer → sell) when enabled (M4.1)
        2. Verified source / ABI (when a ContractSourceProvider is configured)
        3. Runtime bytecode selector heuristics
    """

    def __init__(
        self,
        web3: AsyncWeb3,
        *,
        chain_id: int | None = None,
        source_provider: ContractSourceProvider | None = None,
        simulation_provider: HoneypotSimulationProvider | None = None,
        source_engine: SourceAnalysisEngine | None = None,
    ) -> None:
        self._web3 = web3
        self._chain_id = chain_id
        self._source_provider = source_provider or NullContractSourceProvider()
        self._simulation_provider = simulation_provider or NullHoneypotSimulationProvider()
        self._source_engine = source_engine or SourceAnalysisEngine()

    async def analyze(
        self,
        contract_address: str,
        *,
        bytecode: bytes | None = None,
        implementation_address: str | None = None,
        implementation_bytecode: bytes | None = None,
    ) -> HoneypotAnalysisData:
        """
        Analyze the logic-bearing contract for honeypot indicators.

        Proxies are scanned at the implementation layer — identical to CapabilityAnalyzer.
        """
        logic_address = implementation_address or contract_address
        logic_bytecode = implementation_bytecode

        if logic_bytecode is None and bytecode is not None and not implementation_address:
            logic_bytecode = bytecode

        if logic_bytecode is None:
            checksum = AsyncWeb3.to_checksum_address(normalize_eth_address(logic_address))
            try:
                on_chain_code = await self._web3.eth.get_code(checksum)
                logic_bytecode = bytes(on_chain_code)
            except Exception:
                logger.exception("eth_getCode failed for honeypot scan on %s", logic_address)
                logic_bytecode = b""

        abi_function_names, source_verified, source_analysis = await self._resolve_source_context(
            logic_address,
        )
        simulation_result = await self._run_trade_simulation(logic_address)

        simulation = build_not_run_simulation_state()
        can_buy: bool | None = None
        can_sell: bool | None = None
        can_transfer: bool | None = None
        buy_tax_bps: int | None = None
        sell_tax_bps: int | None = None
        trade_simulated = False

        if simulation_result is not None and simulation_result.simulated:
            trade_simulated = True
            can_buy = simulation_result.can_buy
            can_sell = simulation_result.can_sell
            can_transfer = simulation_result.can_transfer
            buy_tax_bps = simulation_result.buy_tax_bps
            sell_tax_bps = simulation_result.sell_tax_bps
            if simulation_result.simulation is not None:
                simulation = simulation_result.simulation

        findings = build_honeypot_findings(
            logic_bytecode=logic_bytecode or b"",
            abi_function_names=abi_function_names,
            source_verified=source_verified,
            trade_simulated=trade_simulated,
            can_buy=can_buy,
            can_sell=can_sell,
            can_transfer=can_transfer,
            buy_tax_bps=buy_tax_bps,
            sell_tax_bps=sell_tax_bps,
        )
        findings = merge_source_into_honeypot_findings(findings, source_analysis)
        summary = build_honeypot_summary(findings, simulation=simulation)
        heuristic_flags = legacy_flags_from_findings(findings)
        simulation_flags = (
            simulation_result.to_honeypot_flags()
            if simulation_result is not None
            else HoneypotFlags()
        )
        flags = merge_honeypot_flags(heuristic_flags, simulation_flags)
        method = aggregate_detection_method(findings)

        if simulation_result is not None and simulation_result.simulated:
            if method == HoneypotDetectionMethod.NONE:
                method = HoneypotDetectionMethod.SIMULATION
        elif method == HoneypotDetectionMethod.NONE and flags.has_any:
            method = HoneypotDetectionMethod.BYTECODE

        return HoneypotAnalysisData(
            trading_enabled_control=flags.trading_enabled_control,
            whitelist_control=flags.whitelist_control,
            blacklist_sell_blocking=flags.blacklist_sell_blocking,
            transfer_tax_control=flags.transfer_tax_control,
            can_buy=can_buy,
            can_sell=can_sell,
            buy_tax_bps=buy_tax_bps,
            sell_tax_bps=sell_tax_bps,
            trade_simulated=trade_simulated,
            detection_method=method,
            summary=summary,
            findings=findings,
            simulation=simulation,
        )

    async def _run_trade_simulation(
        self,
        logic_address: str,
    ) -> HoneypotSimulationResult | None:
        if self._chain_id is None:
            return None

        result = await self._simulation_provider.simulate_trade_paths(
            logic_address,
            self._chain_id,
        )
        if result is None or not result.simulated:
            return None
        return result

    async def _resolve_source_context(
        self,
        logic_address: str,
    ) -> tuple[set[str] | None, bool, SourceAnalysisResult | None]:
        if self._chain_id is None:
            return None, False, None

        verified = await self._source_provider.get_verified_source(logic_address, self._chain_id)
        source_analysis = self._source_engine.analyze(verified)
        if verified is None:
            return None, False, None

        fallback_names: set[str] | None = None
        if verified.abi:
            fallback_names = _abi_function_names(verified.abi)
        else:
            import re

            matches = re.findall(r"function\s+(\w+)\s*\(", verified.source_code)
            if matches:
                fallback_names = {name.lower() for name in matches}

        abi_names = merge_abi_function_names(source_analysis, fallback_names)
        return abi_names, True, source_analysis

    async def _resolve_abi_function_names(
        self,
        logic_address: str,
    ) -> tuple[set[str], bool]:
        names, verified, _ = await self._resolve_source_context(logic_address)
        return names or set(), verified
