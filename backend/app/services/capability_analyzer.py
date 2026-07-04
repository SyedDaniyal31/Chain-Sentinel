"""M3 dangerous contract capability detection with controller attribution."""

import logging

from web3 import AsyncWeb3

from app.blockchain.capability import detect_capabilities_from_bytecode
from app.blockchain.capability_intelligence import (
    aggregate_detection_method,
    build_capability_inventory,
    enabled_capability_count,
    legacy_flags_from_inventory,
)
from app.blockchain.contract_source_provider import ContractSourceProvider, NullContractSourceProvider, VerifiedContractSource
from app.blockchain.source_analysis_engine import SourceAnalysisEngine, merge_abi_function_names
from app.core.validators import normalize_eth_address
from app.schemas.scan_result import CapabilityAnalysisData, GovernanceRoleData

logger = logging.getLogger(__name__)


class CapabilityAnalyzer:
    """
    Detect dangerous contract powers and determine who controls them.

    Methods (priority):
        1. Verified source pattern analysis (M4.2 SourceAnalysisEngine)
        2. Verified ABI / source inspection
        3. AccessControl role mapping (from M2 governance)
        4. Runtime bytecode selector heuristics
        5. Trade simulation enrichment for fee capabilities
    """

    def __init__(
        self,
        web3: AsyncWeb3,
        *,
        chain_id: int | None = None,
        source_provider: ContractSourceProvider | None = None,
        source_engine: SourceAnalysisEngine | None = None,
    ) -> None:
        self._web3 = web3
        self._chain_id = chain_id
        self._source_provider = source_provider or NullContractSourceProvider()
        self._source_engine = source_engine or SourceAnalysisEngine()

    async def analyze(
        self,
        contract_address: str,
        *,
        bytecode: bytes | None = None,
        implementation_address: str | None = None,
        implementation_bytecode: bytes | None = None,
        governance_roles: list[GovernanceRoleData] | None = None,
        governance_ownership_address: str | None = None,
        admin_address: str | None = None,
        owner_address: str | None = None,
        trade_simulated: bool = False,
        buy_tax_bps: int | None = None,
        sell_tax_bps: int | None = None,
        transfer_tax_control: bool = False,
        trading_enabled_control: bool = False,
        whitelist_control: bool = False,
    ) -> CapabilityAnalysisData:
        """
        Analyze the logic-bearing contract for dangerous capabilities.

        When a proxy exposes an implementation address, capability probes target
        the implementation — not the thin proxy shell.
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
                logger.exception("eth_getCode failed for capability scan on %s", logic_address)
                logic_bytecode = b""

        verified, source_analysis = await self._resolve_source_analysis(
            logic_address,
            ownership_address=governance_ownership_address,
        )
        abi_function_names = merge_abi_function_names(
            source_analysis,
            await self._abi_names_from_verified(verified),
        )
        source_verified = verified is not None

        inventory = build_capability_inventory(
            logic_bytecode=logic_bytecode,
            abi_function_names=abi_function_names,
            governance_roles=governance_roles,
            ownership_address=governance_ownership_address,
            admin_address=admin_address,
            owner_address=owner_address,
            trade_simulated=trade_simulated,
            buy_tax_bps=buy_tax_bps,
            sell_tax_bps=sell_tax_bps,
            transfer_tax_control=transfer_tax_control,
            trading_enabled_control=trading_enabled_control,
            whitelist_control=whitelist_control,
            source_verified=source_verified,
            source_analysis=source_analysis,
        )

        mint_capability, pause_capability, blacklist_capability, ownership_capability = (
            legacy_flags_from_inventory(inventory)
        )

        return CapabilityAnalysisData(
            mint_capability=mint_capability,
            pause_capability=pause_capability,
            blacklist_capability=blacklist_capability,
            ownership_capability=ownership_capability,
            detection_method=aggregate_detection_method(inventory),
            capability_count=enabled_capability_count(inventory),
            capabilities=inventory,
        )

    async def _resolve_source_analysis(
        self,
        logic_address: str,
        *,
        ownership_address: str | None,
    ):
        if self._chain_id is None:
            return None, None

        verified = await self._source_provider.get_verified_source(logic_address, self._chain_id)
        source_analysis = self._source_engine.analyze(
            verified,
            ownership_address=ownership_address,
        )
        return verified, source_analysis

    async def _abi_names_from_verified(
        self,
        verified: VerifiedContractSource | None,
    ) -> set[str] | None:
        if verified is None:
            return None

        if verified.abi:
            return {
                entry["name"]
                for entry in verified.abi
                if entry.get("type") == "function" and isinstance(entry.get("name"), str)
            }

        import re

        matches = re.findall(r"function\s+(\w+)\s*\(", verified.source_code)
        if matches:
            return set(matches)

        return None
