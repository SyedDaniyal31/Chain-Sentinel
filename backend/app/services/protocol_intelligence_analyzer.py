"""M6.0 protocol classification orchestrator."""

from __future__ import annotations

import logging

from web3 import AsyncWeb3

from app.blockchain.protocol.models import ProtocolDetectionContext
from app.blockchain.protocol_intelligence import build_protocol_intelligence
from app.core.validators import normalize_eth_address
from app.schemas.scan_result import ProtocolIntelligenceData

logger = logging.getLogger(__name__)


class ProtocolIntelligenceAnalyzer:
    """
    Classify protocol family, standards, frameworks, proxy type, and integrations.

    Runs after wallet intelligence and before RiskEngine in ContractAnalyzer.
    """

    def __init__(self, web3: AsyncWeb3) -> None:
        self._web3 = web3

    async def analyze(
        self,
        target_address: str,
        *,
        bytecode: bytes,
        chain_id: int = 1,
        implementation_bytecode: bytes | None = None,
        implementation_address: str | None = None,
        admin_address: str | None = None,
        is_timelock: bool = False,
        is_verified: bool = False,
        verified_source_code: str | None = None,
        contract_name: str | None = None,
    ) -> ProtocolIntelligenceData:
        normalized = normalize_eth_address(target_address)
        logic_bytecode = implementation_bytecode if implementation_bytecode is not None else bytecode

        if not bytecode:
            return ProtocolIntelligenceData()

        context = ProtocolDetectionContext(
            target_address=normalized,
            bytecode=bytecode,
            logic_bytecode=logic_bytecode,
            chain_id=chain_id,
            implementation_address=implementation_address.lower() if implementation_address else None,
            admin_address=admin_address.lower() if admin_address else None,
            is_timelock_hint=is_timelock,
            is_verified=is_verified,
            verified_source_code=verified_source_code,
            contract_name=contract_name,
        )

        try:
            return await build_protocol_intelligence(self._web3, context)
        except Exception:
            logger.debug(
                "Protocol intelligence analysis failed for %s",
                normalized,
                exc_info=True,
            )
            return ProtocolIntelligenceData()
