"""M6.4 threat surface intelligence orchestrator."""

from __future__ import annotations

import logging

from app.blockchain.security.threat_surface_analyzer import (
    build_threat_context_from_scan,
    enrich_protocol_with_threat_surface,
)
from app.core.validators import normalize_eth_address
from app.schemas.scan_result import ProtocolIntelligenceData

logger = logging.getLogger(__name__)


class ThreatSurfaceAnalyzer:
    """
    Infer security-relevant attack surfaces from protocol relationships and scan intelligence.

    Runs after ProtocolRelationshipAnalyzer and before RiskEngine in ContractAnalyzer.
    Does not modify RiskEngine scoring.
    """

    def analyze(
        self,
        target_address: str,
        *,
        protocol_intelligence: ProtocolIntelligenceData,
        governance_type: object | None = None,
        upgrade_authority: object | None = None,
        governance_ownership_address: str | None = None,
        governance_ownership_renounced: bool = False,
        has_timelock: bool = False,
        is_verified: bool = False,
        is_upgradeable: bool = False,
        implementation_address: str | None = None,
        admin_address: str | None = None,
        owner_address: str | None = None,
        capabilities_detail: dict | None = None,
        mint_capability: bool = False,
        pause_capability: bool = False,
        honeypot_is_suspected: bool = False,
        honeypot_is_confirmed: bool = False,
        liquidity_has_liquidity: bool = False,
        liquidity_primary_dex: str | None = None,
        liquidity_pair_address: str | None = None,
        liquidity_usd: object | None = None,
        wallet_creator: str | None = None,
        wallet_deployer: str | None = None,
        wallet_owner: str | None = None,
        wallet_treasury: str | None = None,
        treasury_is_multisig: bool = False,
    ) -> ProtocolIntelligenceData:
        normalized = normalize_eth_address(target_address)

        if not protocol_intelligence:
            return ProtocolIntelligenceData()

        try:
            context = build_threat_context_from_scan(
                target_address=normalized,
                protocol=protocol_intelligence,
                governance_type=governance_type,
                upgrade_authority=upgrade_authority,
                governance_ownership_address=governance_ownership_address,
                governance_ownership_renounced=governance_ownership_renounced,
                has_timelock=has_timelock,
                is_verified=is_verified,
                is_upgradeable=is_upgradeable,
                implementation_address=implementation_address,
                admin_address=admin_address,
                owner_address=owner_address,
                capabilities_detail=capabilities_detail,
                mint_capability=mint_capability,
                pause_capability=pause_capability,
                honeypot_is_suspected=honeypot_is_suspected,
                honeypot_is_confirmed=honeypot_is_confirmed,
                liquidity_has_liquidity=liquidity_has_liquidity,
                liquidity_primary_dex=liquidity_primary_dex,
                liquidity_pair_address=liquidity_pair_address,
                liquidity_usd=liquidity_usd,
                wallet_creator=wallet_creator,
                wallet_deployer=wallet_deployer,
                wallet_owner=wallet_owner,
                wallet_treasury=wallet_treasury,
                treasury_is_multisig=treasury_is_multisig,
            )
            return enrich_protocol_with_threat_surface(protocol_intelligence, context)
        except Exception:
            logger.debug(
                "Threat surface analysis failed for %s",
                normalized,
                exc_info=True,
            )
            return protocol_intelligence
