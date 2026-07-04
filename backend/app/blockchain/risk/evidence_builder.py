"""Adapters that translate analyzer outputs into unified risk evidence (M7.1)."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.blockchain.risk.evidence import create_evidence, merge_evidence
from app.blockchain.risk.evidence_types import (
    EvidenceCategory,
    EvidenceMetadataKey,
    EvidenceSeverity,
    EvidenceSource,
)
from app.blockchain.risk.models import RiskEvidence
from app.models.enums import AdminType, ConfidenceLevel, ContractType, ProxyType, ScanDetectionMethod
from app.schemas.risk import ContractRiskInput
from app.schemas.scan_result import (
    AttackPathData,
    ExternalDependencyData,
    GovernanceAnalysisData,
    LiquidityAnalysisData,
    PrivilegedEntityData,
    ProtocolIntelligenceData,
    ProtocolRelationshipData,
    ThreatSurfaceData,
    TrustBoundaryData,
    WalletIntelligenceData,
)
from app.blockchain.risk.scoring_weights import (
    CONFIDENCE_BYTECODE_CONFIRMED,
    CONFIDENCE_CLASSIFICATION,
    CONFIDENCE_DETECTION_BYTECODE,
    CONFIDENCE_DETECTION_HYBRID,
    CONFIDENCE_DETECTION_NONE,
    CONFIDENCE_DETECTION_SIMULATION,
    CONFIDENCE_DETECTION_SOURCE,
    CONFIDENCE_PROXY_RESOLVED,
    CONFIDENCE_PROXY_UNRESOLVED_PENALTY,
    CONFIDENCE_TRADE_SIMULATED,
    CONFIDENCE_VERIFIED_SOURCE,
    HIGH_TAX_BPS_THRESHOLD,
    LOW_LIQUIDITY_USD,
    REASON_ADMIN_CONTRACT,
    REASON_ADMIN_EOA,
    REASON_ADMIN_MULTISIG,
    REASON_BLACKLIST_CAPABILITY,
    REASON_BLACKLIST_SELL_BLOCKING,
    REASON_CREATOR_OWNS_MAJORITY,
    REASON_EXCHANGE_FUNDED_DEPLOYER,
    REASON_FRESH_DEPLOYER,
    REASON_IMPLEMENTATION,
    REASON_LP_OWNER_IS_CREATOR,
    REASON_LOW_LIQUIDITY,
    REASON_MINT_CAPABILITY,
    REASON_NO_LIQUIDITY,
    REASON_NO_UPGRADE_SIGNALS,
    REASON_NOT_CONTRACT,
    REASON_OWNERSHIP_CAPABILITY,
    REASON_PAUSE_CAPABILITY,
    REASON_PROXYADMIN_OWNER,
    REASON_SIM_BUY_BLOCKED,
    REASON_SIM_HIGH_BUY_TAX,
    REASON_SIM_HIGH_SELL_TAX,
    REASON_SIM_SELL_BLOCKED,
    REASON_SINGLE_WALLET_LP,
    REASON_TORNADO_FUNDED_DEPLOYER,
    REASON_TREASURY_MULTISIG,
    REASON_TRADING_ENABLED_CONTROL,
    REASON_TRANSFER_TAX_CONTROL,
    REASON_UNLOCKED_LP,
    REASON_UPGRADEABLE,
    REASON_WALLET_KNOWN_SCAM,
    REASON_WHITELIST_CONTROL,
    SCORE_ADMIN_CONTRACT,
    SCORE_ADMIN_EOA,
    SCORE_ADMIN_MULTISIG,
    SCORE_ADMIN_TIMELOCK,
    SCORE_BLACKLIST_CAPABILITY,
    SCORE_BLACKLIST_SELL_BLOCKING,
    SCORE_CREATOR_OWNS_MAJORITY,
    SCORE_EXCHANGE_FUNDED_DEPLOYER,
    SCORE_FRESH_DEPLOYER,
    SCORE_IMPLEMENTATION,
    SCORE_LP_OWNER_IS_CREATOR,
    SCORE_LOW_LIQUIDITY,
    SCORE_MINT_CAPABILITY,
    SCORE_NO_LIQUIDITY,
    SCORE_OWNERSHIP_CAPABILITY,
    SCORE_PAUSE_CAPABILITY,
    SCORE_SIM_BUY_BLOCKED,
    SCORE_SIM_HIGH_BUY_TAX,
    SCORE_SIM_HIGH_SELL_TAX,
    SCORE_SIM_SELL_BLOCKED,
    SCORE_SINGLE_WALLET_LP,
    SCORE_TORNADO_FUNDED_DEPLOYER,
    SCORE_TRADING_ENABLED_CONTROL,
    SCORE_TRANSFER_TAX_CONTROL,
    SCORE_TREASURY_MULTISIG,
    SCORE_UNLOCKED_LP,
    SCORE_UPGRADEABLE,
    SCORE_WALLET_KNOWN_SCAM,
    SCORE_WHITELIST_CONTROL,
    THREAT_BLACKLIST,
    THREAT_BLACKLIST_SELL,
    THREAT_IMPLEMENTATION,
    THREAT_LOW_LIQUIDITY,
    THREAT_MINT,
    THREAT_NO_LIQUIDITY,
    THREAT_OWNERSHIP,
    THREAT_PAUSE,
    THREAT_SIM_BUY_BLOCKED,
    THREAT_SIM_HIGH_BUY_TAX,
    THREAT_SIM_HIGH_SELL_TAX,
    THREAT_SIM_SELL_BLOCKED,
    THREAT_TRANSFER_TAX,
    THREAT_UNLOCKED_LP,
    THREAT_UPGRADEABLE,
    THREAT_WHITELIST,
    THREAT_TRADING_ENABLED,
    CENTRAL_ADMIN_CONTRACT,
    CENTRAL_ADMIN_EOA,
    CENTRAL_ADMIN_MULTISIG,
    CENTRAL_ADMIN_TIMELOCK,
    CENTRAL_OWNERSHIP_CAPABILITY,
    CENTRAL_UPGRADEABLE_UNKNOWN_ADMIN,
    timelock_reason,
)


_BURN_ADDRESSES = {
    "0x0000000000000000000000000000000000000000",
    "0x000000000000000000000000000000000000dead",
}


@dataclass(frozen=True, slots=True)
class RiskEvidenceBundle:
    """Optional analyzer outputs collected before evidence normalization."""

    contract_input: ContractRiskInput | None = None
    governance: GovernanceAnalysisData | None = None
    liquidity: LiquidityAnalysisData | None = None
    wallet: WalletIntelligenceData | None = None
    protocol: ProtocolIntelligenceData | None = None
    threat_surface: ThreatSurfaceData | None = None


class RiskEvidenceBuilder:
    """Translate analyzer-specific outputs into unified RiskEvidence objects."""

    def build(self, bundle: RiskEvidenceBundle) -> list[RiskEvidence]:
        """Merge scoring evidence and supplemental analyzer evidence."""
        scoring: list[RiskEvidence] = []
        supplemental: list[RiskEvidence] = []

        if bundle.contract_input is not None:
            scoring.extend(self.from_contract_risk_input(bundle.contract_input))
        else:
            if bundle.governance is not None:
                scoring.extend(self.from_governance_analysis(bundle.governance))
            if bundle.liquidity is not None:
                scoring.extend(self.from_liquidity_analysis(bundle.liquidity))
            if bundle.wallet is not None:
                scoring.extend(self.from_wallet_intelligence(bundle.wallet))

        if bundle.protocol is not None:
            supplemental.extend(self.from_protocol_intelligence(bundle.protocol))
            supplemental.extend(
                self.from_protocol_relationship_analysis(bundle.protocol.relationships)
            )
            supplemental.extend(
                self.from_threat_surface_analysis(bundle.protocol.threat_surface)
            )
        elif bundle.threat_surface is not None:
            supplemental.extend(self.from_threat_surface_analysis(bundle.threat_surface))

        return merge_evidence(scoring, supplemental)

    def from_contract_risk_input(self, findings: ContractRiskInput) -> list[RiskEvidence]:
        """Adapter for the flattened ContractRiskInput consumed by legacy scans."""
        if not findings.is_contract:
            return [
                create_evidence(
                    source=EvidenceSource.SYSTEM,
                    category=EvidenceCategory.SYSTEM,
                    signal="not_contract",
                    severity=EvidenceSeverity.INFO,
                    score=Decimal("0.00"),
                    confidence=ConfidenceLevel.HIGH,
                    reason=REASON_NOT_CONTRACT,
                    metadata={
                        EvidenceMetadataKey.CONFIDENCE_WEIGHT.value: 45,
                        EvidenceMetadataKey.SIGNAL.value: "not_contract",
                    },
                )
            ]

        evidence: list[RiskEvidence] = []

        if findings.is_upgradeable:
            evidence.append(
                create_evidence(
                    source=EvidenceSource.PROXY,
                    category=EvidenceCategory.UPGRADEABILITY,
                    signal="upgradeable",
                    severity=EvidenceSeverity.MEDIUM,
                    score=SCORE_UPGRADEABLE,
                    confidence=ConfidenceLevel.MEDIUM,
                    reason=REASON_UPGRADEABLE,
                    metadata={
                        EvidenceMetadataKey.THREAT_WEIGHT.value: THREAT_UPGRADEABLE,
                        EvidenceMetadataKey.CENTRALIZATION_WEIGHT.value: CENTRAL_UPGRADEABLE_UNKNOWN_ADMIN
                        if not findings.admin_address
                        else 0,
                        EvidenceMetadataKey.SIGNAL.value: "is_upgradeable",
                    },
                )
            )

        if findings.implementation_address:
            evidence.append(
                create_evidence(
                    source=EvidenceSource.PROXY,
                    category=EvidenceCategory.UPGRADEABILITY,
                    signal="implementation_exposed",
                    severity=EvidenceSeverity.MEDIUM,
                    score=SCORE_IMPLEMENTATION,
                    confidence=ConfidenceLevel.MEDIUM,
                    reason=REASON_IMPLEMENTATION,
                    metadata={
                        EvidenceMetadataKey.THREAT_WEIGHT.value: THREAT_IMPLEMENTATION,
                        EvidenceMetadataKey.CONFIDENCE_WEIGHT.value: CONFIDENCE_PROXY_RESOLVED,
                        EvidenceMetadataKey.SIGNAL.value: "implementation_address",
                    },
                )
            )
        elif findings.is_upgradeable:
            evidence.append(
                create_evidence(
                    source=EvidenceSource.PROXY,
                    category=EvidenceCategory.CONFIDENCE,
                    signal="proxy_unresolved",
                    severity=EvidenceSeverity.LOW,
                    score=Decimal("0.00"),
                    confidence=ConfidenceLevel.LOW,
                    reason="Upgradeable proxy without resolved implementation",
                    metadata={
                        EvidenceMetadataKey.CONFIDENCE_WEIGHT.value: -CONFIDENCE_PROXY_UNRESOLVED_PENALTY,
                        EvidenceMetadataKey.SIGNAL.value: "proxy_unresolved",
                    },
                )
            )

        if findings.admin_address:
            admin_score, admin_reason, central_weight = self._admin_evidence_weights(findings)
            evidence.append(
                create_evidence(
                    source=EvidenceSource.GOVERNANCE,
                    category=EvidenceCategory.AUTHORITY,
                    signal="admin_authority",
                    severity=self._severity_for_score(admin_score),
                    score=admin_score,
                    confidence=ConfidenceLevel.MEDIUM,
                    reason=admin_reason,
                    metadata={
                        EvidenceMetadataKey.CENTRALIZATION_WEIGHT.value: central_weight,
                        EvidenceMetadataKey.IS_TIMELOCK.value: findings.is_timelock,
                        EvidenceMetadataKey.MIN_DELAY.value: findings.min_delay,
                        EvidenceMetadataKey.ADMIN_TYPE.value: (
                            findings.admin_type.value if findings.admin_type else None
                        ),
                        EvidenceMetadataKey.OWNER_TYPE.value: (
                            findings.owner_type.value if findings.owner_type else None
                        ),
                        EvidenceMetadataKey.SIGNAL.value: "admin_address",
                    },
                )
            )
            if findings.owner_address and findings.admin_type == AdminType.CONTRACT:
                evidence.append(
                    create_evidence(
                        source=EvidenceSource.GOVERNANCE,
                        category=EvidenceCategory.AUTHORITY,
                        signal="proxyadmin_owner",
                        severity=EvidenceSeverity.INFO,
                        score=Decimal("0.00"),
                        confidence=ConfidenceLevel.MEDIUM,
                        reason=REASON_PROXYADMIN_OWNER,
                        metadata={
                            EvidenceMetadataKey.REASON_ONLY.value: True,
                            EvidenceMetadataKey.SIGNAL.value: "proxyadmin_owner",
                        },
                    )
                )

        evidence.extend(self._capability_evidence(findings))
        evidence.extend(self._honeypot_evidence(findings))
        evidence.extend(self._simulation_evidence(findings))

        if findings.liquidity_analyzed:
            evidence.extend(self._liquidity_evidence_from_input(findings))

        if findings.wallet_analyzed:
            evidence.extend(self._wallet_evidence_from_input(findings))

        evidence.extend(self._classification_confidence_evidence(findings))

        has_risk_reason = any(
            item.score > 0 or item.metadata.get(EvidenceMetadataKey.REASON_ONLY.value)
            for item in evidence
            if item.category != EvidenceCategory.CONFIDENCE
        )
        if not has_risk_reason:
            evidence.append(
                create_evidence(
                    source=EvidenceSource.SYSTEM,
                    category=EvidenceCategory.SYSTEM,
                    signal="no_upgrade_signals",
                    severity=EvidenceSeverity.INFO,
                    score=Decimal("0.00"),
                    confidence=ConfidenceLevel.MEDIUM,
                    reason=REASON_NO_UPGRADE_SIGNALS,
                    metadata={EvidenceMetadataKey.SIGNAL.value: "no_upgrade_signals"},
                )
            )

        return evidence

    def from_governance_analysis(self, data: GovernanceAnalysisData) -> list[RiskEvidence]:
        """Adapter for GovernanceAnalyzer output (informational until full correlation)."""
        evidence: list[RiskEvidence] = []
        if data.governance_type.value != "none":
            evidence.append(
                create_evidence(
                    source=EvidenceSource.GOVERNANCE,
                    category=EvidenceCategory.AUTHORITY,
                    signal="governance_type",
                    severity=EvidenceSeverity.INFO,
                    score=Decimal("0.00"),
                    confidence=data.source_confidence,
                    reason=f"Governance type detected: {data.governance_type.value}",
                    metadata={
                        EvidenceMetadataKey.SIGNAL.value: "governance_type",
                        "governance_type": data.governance_type.value,
                        "upgrade_authority": data.upgrade_authority.value,
                    },
                )
            )
        if data.has_timelock:
            evidence.append(
                create_evidence(
                    source=EvidenceSource.GOVERNANCE,
                    category=EvidenceCategory.AUTHORITY,
                    signal="timelock",
                    severity=EvidenceSeverity.LOW,
                    score=Decimal("0.00"),
                    confidence=data.source_confidence,
                    reason="Timelock governance detected",
                    metadata={EvidenceMetadataKey.SIGNAL.value: "has_timelock"},
                )
            )
        if data.ownership_renounced:
            evidence.append(
                create_evidence(
                    source=EvidenceSource.GOVERNANCE,
                    category=EvidenceCategory.AUTHORITY,
                    signal="ownership_renounced",
                    severity=EvidenceSeverity.INFO,
                    score=Decimal("0.00"),
                    confidence=data.source_confidence,
                    reason="Contract ownership appears renounced",
                    metadata={EvidenceMetadataKey.SIGNAL.value: "ownership_renounced"},
                )
            )
        for role in data.roles:
            evidence.append(
                create_evidence(
                    source=EvidenceSource.GOVERNANCE,
                    category=EvidenceCategory.AUTHORITY,
                    signal=f"role:{role.role_id}",
                    severity=EvidenceSeverity.INFO,
                    score=Decimal("0.00"),
                    confidence=data.source_confidence,
                    reason=f"AccessControl role detected: {role.name}",
                    metadata={
                        EvidenceMetadataKey.SIGNAL.value: "governance_role",
                        "role_name": role.name,
                        "role_id": role.role_id,
                    },
                )
            )
        return evidence

    def from_liquidity_analysis(self, data: LiquidityAnalysisData) -> list[RiskEvidence]:
        """Adapter for LiquidityIntelligenceAnalyzer output."""
        return self._liquidity_evidence(
            has_liquidity=data.has_liquidity,
            liquidity_usd=data.liquidity_usd,
            liquidity_locked=data.liquidity_locked,
            liquidity_lock_percentage=data.liquidity_lock_percentage,
            lp_owner=data.lp_owner,
            primary_dex=data.primary_dex,
        )

    def from_wallet_intelligence(self, data: WalletIntelligenceData) -> list[RiskEvidence]:
        """Adapter for WalletIntelligenceAnalyzer output."""
        return self._wallet_evidence(
            deployer_is_fresh=data.deployer_is_fresh,
            creator_owns_majority=data.creator_owns_majority,
            lp_owner_is_creator=data.lp_owner_is_creator,
            exchange_funded_deployer=data.exchange_funded_deployer,
            tornado_funded_deployer=data.tornado_funded_deployer,
            treasury_is_multisig=data.treasury_is_multisig,
            wallet_known_scam=data.reputation.known_scam or data.reputation.sanctioned,
        )

    def from_protocol_intelligence(self, data: ProtocolIntelligenceData) -> list[RiskEvidence]:
        """Adapter for ProtocolIntelligenceAnalyzer output."""
        evidence: list[RiskEvidence] = []
        if data.protocol_family != "unknown" or data.protocol_name != "unknown":
            evidence.append(
                create_evidence(
                    source=EvidenceSource.PROTOCOL,
                    category=EvidenceCategory.PROTOCOL,
                    signal="protocol_identity",
                    severity=EvidenceSeverity.INFO,
                    score=Decimal("0.00"),
                    confidence=data.confidence.level,
                    reason=f"Protocol classified as {data.name} ({data.family})",
                    metadata={
                        EvidenceMetadataKey.SIGNAL.value: "protocol_identity",
                        "protocol_family": data.family,
                        "protocol_name": data.name,
                        "protocol_type": data.protocol_type,
                    },
                )
            )
        for integration_group, label in (
            (data.dexes, "dex"),
            (data.lending, "lending"),
            (data.oracles, "oracle"),
            (data.bridges, "bridge"),
            (data.vaults, "vault"),
            (data.nfts, "nft"),
            (data.governance, "governance_integration"),
        ):
            for index, item in enumerate(integration_group):
                name = getattr(item, "name", None) or getattr(item, "standard", "unknown")
                evidence.append(
                    create_evidence(
                        source=EvidenceSource.PROTOCOL,
                        category=EvidenceCategory.PROTOCOL,
                        signal=f"{label}:{index}:{name}",
                        severity=EvidenceSeverity.INFO,
                        score=Decimal("0.00"),
                        confidence=self._confidence_from_score(getattr(item, "confidence", 0)),
                        reason=f"{label.title()} integration detected: {name}",
                        metadata={
                            EvidenceMetadataKey.SIGNAL.value: f"protocol_{label}",
                            EvidenceMetadataKey.ENTITY_NAME.value: str(name),
                        },
                    )
                )
        for reason in data.detection_reasons:
            evidence.append(
                create_evidence(
                    source=EvidenceSource.PROTOCOL,
                    category=EvidenceCategory.PROTOCOL,
                    signal=f"detection_reason:{reason[:48]}",
                    severity=EvidenceSeverity.INFO,
                    score=Decimal("0.00"),
                    confidence=data.confidence.level,
                    reason=reason,
                    metadata={EvidenceMetadataKey.SIGNAL.value: "detection_reason"},
                )
            )
        return evidence

    def from_protocol_relationship_analysis(
        self,
        relationships: list[ProtocolRelationshipData],
    ) -> list[RiskEvidence]:
        """Adapter for ProtocolRelationshipAnalyzer output."""
        evidence: list[RiskEvidence] = []
        for index, relationship in enumerate(relationships):
            evidence.append(
                create_evidence(
                    source=EvidenceSource.RELATIONSHIP,
                    category=EvidenceCategory.RELATIONSHIP,
                    signal=f"relationship:{index}",
                    severity=EvidenceSeverity.INFO,
                    score=Decimal("0.00"),
                    confidence=self._confidence_from_score(relationship.confidence),
                    reason=(
                        f"{relationship.source} {relationship.relationship_type} "
                        f"{relationship.target}"
                    ),
                    metadata={
                        EvidenceMetadataKey.SIGNAL.value: "protocol_relationship",
                        EvidenceMetadataKey.RELATIONSHIP_TYPE.value: relationship.relationship_type,
                        "source": relationship.source,
                        "target": relationship.target,
                        "detection_source": relationship.detection_source,
                    },
                )
            )
        return evidence

    def from_threat_surface_analysis(self, data: ThreatSurfaceData) -> list[RiskEvidence]:
        """Adapter for ThreatSurfaceAnalyzer output."""
        evidence: list[RiskEvidence] = []
        evidence.extend(self._threat_items(data.external_dependencies, ExternalDependencyData, "dependency"))
        evidence.extend(self._threat_items(data.trust_boundaries, TrustBoundaryData, "trust_boundary"))
        evidence.extend(self._threat_items(data.privileged_entities, PrivilegedEntityData, "privileged_entity"))
        evidence.extend(self._attack_path_items(data.attack_paths))
        for index, asset in enumerate(data.critical_assets):
            evidence.append(
                create_evidence(
                    source=EvidenceSource.THREAT_SURFACE,
                    category=EvidenceCategory.THREAT,
                    signal=f"critical_asset:{index}",
                    severity=EvidenceSeverity.MEDIUM,
                    score=Decimal("0.00"),
                    confidence=self._confidence_from_score(asset.confidence),
                    reason=f"Critical asset identified: {asset.label}",
                    metadata={
                        EvidenceMetadataKey.SIGNAL.value: "critical_asset",
                        EvidenceMetadataKey.ENTITY_NAME.value: asset.label,
                        EvidenceMetadataKey.ENTITY_ADDRESS.value: asset.address,
                        "asset_type": asset.asset_type,
                    },
                )
            )
        return evidence

    @staticmethod
    def _admin_evidence_weights(
        findings: ContractRiskInput,
    ) -> tuple[Decimal, str, int]:
        if findings.is_timelock:
            return (
                Decimal(SCORE_ADMIN_TIMELOCK),
                timelock_reason(findings.min_delay),
                CENTRAL_ADMIN_TIMELOCK,
            )
        effective_type = findings.owner_type if findings.owner_type is not None else findings.admin_type
        if effective_type == AdminType.MULTISIG:
            return Decimal(SCORE_ADMIN_MULTISIG), REASON_ADMIN_MULTISIG, CENTRAL_ADMIN_MULTISIG
        if effective_type == AdminType.CONTRACT:
            return Decimal(SCORE_ADMIN_CONTRACT), REASON_ADMIN_CONTRACT, CENTRAL_ADMIN_CONTRACT
        return Decimal(SCORE_ADMIN_EOA), REASON_ADMIN_EOA, CENTRAL_ADMIN_EOA

    @staticmethod
    def _capability_evidence(findings: ContractRiskInput) -> list[RiskEvidence]:
        mapping = [
            (
                findings.mint_capability,
                "mint_capability",
                SCORE_MINT_CAPABILITY,
                REASON_MINT_CAPABILITY,
                THREAT_MINT,
                EvidenceSeverity.MEDIUM,
            ),
            (
                findings.pause_capability,
                "pause_capability",
                SCORE_PAUSE_CAPABILITY,
                REASON_PAUSE_CAPABILITY,
                THREAT_PAUSE,
                EvidenceSeverity.MEDIUM,
            ),
            (
                findings.blacklist_capability,
                "blacklist_capability",
                SCORE_BLACKLIST_CAPABILITY,
                REASON_BLACKLIST_CAPABILITY,
                THREAT_BLACKLIST,
                EvidenceSeverity.HIGH,
            ),
            (
                findings.ownership_capability,
                "ownership_capability",
                SCORE_OWNERSHIP_CAPABILITY,
                REASON_OWNERSHIP_CAPABILITY,
                THREAT_OWNERSHIP,
                EvidenceSeverity.LOW,
            ),
        ]
        evidence: list[RiskEvidence] = []
        for enabled, signal, score, reason, threat_weight, severity in mapping:
            if not enabled:
                continue
            metadata = {
                EvidenceMetadataKey.THREAT_WEIGHT.value: threat_weight,
                EvidenceMetadataKey.SIGNAL.value: signal,
            }
            if signal == "ownership_capability":
                metadata[EvidenceMetadataKey.CENTRALIZATION_WEIGHT.value] = CENTRAL_OWNERSHIP_CAPABILITY
            evidence.append(
                create_evidence(
                    source=EvidenceSource.CAPABILITY,
                    category=EvidenceCategory.CAPABILITY,
                    signal=signal,
                    severity=severity,
                    score=score,
                    confidence=ConfidenceLevel.MEDIUM,
                    reason=reason,
                    metadata=metadata,
                )
            )
        return evidence

    @staticmethod
    def _honeypot_evidence(findings: ContractRiskInput) -> list[RiskEvidence]:
        simulation_confirmed_sell_block = findings.trade_simulated and findings.can_sell is False
        simulation_confirmed_high_tax = findings.trade_simulated and (
            (findings.sell_tax_bps is not None and findings.sell_tax_bps >= HIGH_TAX_BPS_THRESHOLD)
            or (findings.buy_tax_bps is not None and findings.buy_tax_bps >= HIGH_TAX_BPS_THRESHOLD)
        )
        evidence: list[RiskEvidence] = []
        if findings.trading_enabled_control:
            evidence.append(
                create_evidence(
                    source=EvidenceSource.HONEYPOT,
                    category=EvidenceCategory.HONEYPOT,
                    signal="trading_enabled_control",
                    severity=EvidenceSeverity.MEDIUM,
                    score=SCORE_TRADING_ENABLED_CONTROL,
                    confidence=ConfidenceLevel.MEDIUM,
                    reason=REASON_TRADING_ENABLED_CONTROL,
                    metadata={
                        EvidenceMetadataKey.THREAT_WEIGHT.value: THREAT_TRADING_ENABLED,
                        EvidenceMetadataKey.SIGNAL.value: "trading_enabled_control",
                    },
                )
            )
        if findings.whitelist_control:
            evidence.append(
                create_evidence(
                    source=EvidenceSource.HONEYPOT,
                    category=EvidenceCategory.HONEYPOT,
                    signal="whitelist_control",
                    severity=EvidenceSeverity.MEDIUM,
                    score=SCORE_WHITELIST_CONTROL,
                    confidence=ConfidenceLevel.MEDIUM,
                    reason=REASON_WHITELIST_CONTROL,
                    metadata={
                        EvidenceMetadataKey.THREAT_WEIGHT.value: THREAT_WHITELIST,
                        EvidenceMetadataKey.SIGNAL.value: "whitelist_control",
                    },
                )
            )
        if findings.blacklist_sell_blocking and not simulation_confirmed_sell_block:
            evidence.append(
                create_evidence(
                    source=EvidenceSource.HONEYPOT,
                    category=EvidenceCategory.HONEYPOT,
                    signal="blacklist_sell_blocking",
                    severity=EvidenceSeverity.HIGH,
                    score=SCORE_BLACKLIST_SELL_BLOCKING,
                    confidence=ConfidenceLevel.MEDIUM,
                    reason=REASON_BLACKLIST_SELL_BLOCKING,
                    metadata={
                        EvidenceMetadataKey.THREAT_WEIGHT.value: THREAT_BLACKLIST_SELL,
                        EvidenceMetadataKey.SIGNAL.value: "blacklist_sell_blocking",
                    },
                )
            )
        if findings.transfer_tax_control and not simulation_confirmed_high_tax:
            evidence.append(
                create_evidence(
                    source=EvidenceSource.HONEYPOT,
                    category=EvidenceCategory.HONEYPOT,
                    signal="transfer_tax_control",
                    severity=EvidenceSeverity.MEDIUM,
                    score=SCORE_TRANSFER_TAX_CONTROL,
                    confidence=ConfidenceLevel.MEDIUM,
                    reason=REASON_TRANSFER_TAX_CONTROL,
                    metadata={
                        EvidenceMetadataKey.THREAT_WEIGHT.value: THREAT_TRANSFER_TAX,
                        EvidenceMetadataKey.SIGNAL.value: "transfer_tax_control",
                    },
                )
            )
        return evidence

    @staticmethod
    def _simulation_evidence(findings: ContractRiskInput) -> list[RiskEvidence]:
        if not findings.trade_simulated:
            return []
        evidence: list[RiskEvidence] = []
        if findings.can_buy is False:
            evidence.append(
                create_evidence(
                    source=EvidenceSource.SIMULATION,
                    category=EvidenceCategory.HONEYPOT,
                    signal="sim_buy_blocked",
                    severity=EvidenceSeverity.MEDIUM,
                    score=SCORE_SIM_BUY_BLOCKED,
                    confidence=ConfidenceLevel.HIGH,
                    reason=REASON_SIM_BUY_BLOCKED,
                    metadata={
                        EvidenceMetadataKey.THREAT_WEIGHT.value: THREAT_SIM_BUY_BLOCKED,
                        EvidenceMetadataKey.SIGNAL.value: "sim_buy_blocked",
                    },
                )
            )
        if findings.can_sell is False:
            evidence.append(
                create_evidence(
                    source=EvidenceSource.SIMULATION,
                    category=EvidenceCategory.HONEYPOT,
                    signal="sim_sell_blocked",
                    severity=EvidenceSeverity.CRITICAL,
                    score=SCORE_SIM_SELL_BLOCKED,
                    confidence=ConfidenceLevel.HIGH,
                    reason=REASON_SIM_SELL_BLOCKED,
                    metadata={
                        EvidenceMetadataKey.THREAT_WEIGHT.value: THREAT_SIM_SELL_BLOCKED,
                        EvidenceMetadataKey.FORCE_THREAT_CRITICAL.value: True,
                        EvidenceMetadataKey.SIGNAL.value: "sim_sell_blocked",
                    },
                )
            )
        if findings.buy_tax_bps is not None and findings.buy_tax_bps >= HIGH_TAX_BPS_THRESHOLD:
            evidence.append(
                create_evidence(
                    source=EvidenceSource.SIMULATION,
                    category=EvidenceCategory.HONEYPOT,
                    signal="sim_high_buy_tax",
                    severity=EvidenceSeverity.MEDIUM,
                    score=SCORE_SIM_HIGH_BUY_TAX,
                    confidence=ConfidenceLevel.HIGH,
                    reason=REASON_SIM_HIGH_BUY_TAX.format(tax_bps=findings.buy_tax_bps),
                    metadata={
                        EvidenceMetadataKey.THREAT_WEIGHT.value: THREAT_SIM_HIGH_BUY_TAX,
                        EvidenceMetadataKey.SIGNAL.value: "sim_high_buy_tax",
                    },
                )
            )
        if findings.sell_tax_bps is not None and findings.sell_tax_bps >= HIGH_TAX_BPS_THRESHOLD:
            evidence.append(
                create_evidence(
                    source=EvidenceSource.SIMULATION,
                    category=EvidenceCategory.HONEYPOT,
                    signal="sim_high_sell_tax",
                    severity=EvidenceSeverity.HIGH,
                    score=SCORE_SIM_HIGH_SELL_TAX,
                    confidence=ConfidenceLevel.HIGH,
                    reason=REASON_SIM_HIGH_SELL_TAX.format(tax_bps=findings.sell_tax_bps),
                    metadata={
                        EvidenceMetadataKey.THREAT_WEIGHT.value: THREAT_SIM_HIGH_SELL_TAX,
                        EvidenceMetadataKey.SIGNAL.value: "sim_high_sell_tax",
                    },
                )
            )
        return evidence

    def _liquidity_evidence_from_input(self, findings: ContractRiskInput) -> list[RiskEvidence]:
        return self._liquidity_evidence(
            has_liquidity=findings.has_liquidity,
            liquidity_usd=findings.liquidity_usd,
            liquidity_locked=findings.liquidity_locked,
            liquidity_lock_percentage=findings.liquidity_lock_percentage,
            lp_owner=findings.lp_owner,
            primary_dex=findings.primary_dex,
        )

    def _liquidity_evidence(
        self,
        *,
        has_liquidity: bool,
        liquidity_usd: Decimal,
        liquidity_locked: bool,
        liquidity_lock_percentage: Decimal,
        lp_owner: str | None,
        primary_dex: str | None,
    ) -> list[RiskEvidence]:
        evidence: list[RiskEvidence] = []
        if not has_liquidity:
            evidence.append(
                create_evidence(
                    source=EvidenceSource.LIQUIDITY,
                    category=EvidenceCategory.LIQUIDITY,
                    signal="no_liquidity",
                    severity=EvidenceSeverity.HIGH,
                    score=SCORE_NO_LIQUIDITY,
                    confidence=ConfidenceLevel.MEDIUM,
                    reason=REASON_NO_LIQUIDITY,
                    metadata={
                        EvidenceMetadataKey.THREAT_WEIGHT.value: THREAT_NO_LIQUIDITY,
                        EvidenceMetadataKey.SIGNAL.value: "no_liquidity",
                    },
                )
            )
            return evidence

        if liquidity_usd < LOW_LIQUIDITY_USD:
            evidence.append(
                create_evidence(
                    source=EvidenceSource.LIQUIDITY,
                    category=EvidenceCategory.LIQUIDITY,
                    signal="low_liquidity",
                    severity=EvidenceSeverity.MEDIUM,
                    score=SCORE_LOW_LIQUIDITY,
                    confidence=ConfidenceLevel.MEDIUM,
                    reason=REASON_LOW_LIQUIDITY.format(usd=int(liquidity_usd)),
                    metadata={
                        EvidenceMetadataKey.THREAT_WEIGHT.value: THREAT_LOW_LIQUIDITY,
                        EvidenceMetadataKey.SIGNAL.value: "low_liquidity",
                        "primary_dex": primary_dex,
                    },
                )
            )

        if not liquidity_locked:
            evidence.append(
                create_evidence(
                    source=EvidenceSource.LIQUIDITY,
                    category=EvidenceCategory.LIQUIDITY,
                    signal="unlocked_lp",
                    severity=EvidenceSeverity.MEDIUM,
                    score=SCORE_UNLOCKED_LP,
                    confidence=ConfidenceLevel.MEDIUM,
                    reason=REASON_UNLOCKED_LP,
                    metadata={
                        EvidenceMetadataKey.THREAT_WEIGHT.value: THREAT_UNLOCKED_LP,
                        EvidenceMetadataKey.SIGNAL.value: "unlocked_lp",
                    },
                )
            )

        if (
            lp_owner
            and lp_owner not in _BURN_ADDRESSES
            and liquidity_lock_percentage < Decimal("50.00")
        ):
            evidence.append(
                create_evidence(
                    source=EvidenceSource.LIQUIDITY,
                    category=EvidenceCategory.LIQUIDITY,
                    signal="single_wallet_lp",
                    severity=EvidenceSeverity.MEDIUM,
                    score=SCORE_SINGLE_WALLET_LP,
                    confidence=ConfidenceLevel.MEDIUM,
                    reason=REASON_SINGLE_WALLET_LP,
                    metadata={
                        EvidenceMetadataKey.SIGNAL.value: "single_wallet_lp",
                        EvidenceMetadataKey.ENTITY_ADDRESS.value: lp_owner,
                    },
                )
            )
        return evidence

    def _wallet_evidence_from_input(self, findings: ContractRiskInput) -> list[RiskEvidence]:
        return self._wallet_evidence(
            deployer_is_fresh=findings.deployer_is_fresh,
            creator_owns_majority=findings.creator_owns_majority,
            lp_owner_is_creator=findings.lp_owner_is_creator,
            exchange_funded_deployer=findings.exchange_funded_deployer,
            tornado_funded_deployer=findings.tornado_funded_deployer,
            treasury_is_multisig=findings.treasury_is_multisig,
            wallet_known_scam=findings.wallet_known_scam,
        )

    @staticmethod
    def _wallet_evidence(
        *,
        deployer_is_fresh: bool,
        creator_owns_majority: bool,
        lp_owner_is_creator: bool,
        exchange_funded_deployer: bool,
        tornado_funded_deployer: bool,
        treasury_is_multisig: bool,
        wallet_known_scam: bool,
    ) -> list[RiskEvidence]:
        mapping = [
            (deployer_is_fresh, "fresh_deployer", SCORE_FRESH_DEPLOYER, REASON_FRESH_DEPLOYER, EvidenceSeverity.LOW),
            (
                creator_owns_majority,
                "creator_owns_majority",
                SCORE_CREATOR_OWNS_MAJORITY,
                REASON_CREATOR_OWNS_MAJORITY,
                EvidenceSeverity.HIGH,
            ),
            (
                lp_owner_is_creator,
                "lp_owner_is_creator",
                SCORE_LP_OWNER_IS_CREATOR,
                REASON_LP_OWNER_IS_CREATOR,
                EvidenceSeverity.MEDIUM,
            ),
            (
                exchange_funded_deployer,
                "exchange_funded_deployer",
                SCORE_EXCHANGE_FUNDED_DEPLOYER,
                REASON_EXCHANGE_FUNDED_DEPLOYER,
                EvidenceSeverity.INFO,
            ),
            (
                tornado_funded_deployer,
                "tornado_funded_deployer",
                SCORE_TORNADO_FUNDED_DEPLOYER,
                REASON_TORNADO_FUNDED_DEPLOYER,
                EvidenceSeverity.CRITICAL,
            ),
            (
                treasury_is_multisig,
                "treasury_multisig",
                SCORE_TREASURY_MULTISIG,
                REASON_TREASURY_MULTISIG,
                EvidenceSeverity.INFO,
            ),
            (
                wallet_known_scam,
                "wallet_known_scam",
                SCORE_WALLET_KNOWN_SCAM,
                REASON_WALLET_KNOWN_SCAM,
                EvidenceSeverity.CRITICAL,
            ),
        ]
        evidence: list[RiskEvidence] = []
        for enabled, signal, score, reason, severity in mapping:
            if not enabled:
                continue
            evidence.append(
                create_evidence(
                    source=EvidenceSource.WALLET,
                    category=EvidenceCategory.WALLET,
                    signal=signal,
                    severity=severity,
                    score=score,
                    confidence=ConfidenceLevel.MEDIUM,
                    reason=reason,
                    metadata={EvidenceMetadataKey.SIGNAL.value: signal},
                )
            )
        return evidence

    @staticmethod
    def _classification_confidence_evidence(findings: ContractRiskInput) -> list[RiskEvidence]:
        evidence: list[RiskEvidence] = []
        if findings.is_verified:
            evidence.append(
                create_evidence(
                    source=EvidenceSource.CLASSIFICATION,
                    category=EvidenceCategory.CONFIDENCE,
                    signal="verified_source",
                    severity=EvidenceSeverity.INFO,
                    score=Decimal("0.00"),
                    confidence=ConfidenceLevel.HIGH,
                    reason="Verified contract source available",
                    metadata={
                        EvidenceMetadataKey.CONFIDENCE_WEIGHT.value: CONFIDENCE_VERIFIED_SOURCE,
                        EvidenceMetadataKey.SIGNAL.value: "verified_source",
                    },
                )
            )
        if findings.contract_type is not None and findings.contract_type not in {
            ContractType.UNKNOWN,
            ContractType.EOA,
        }:
            evidence.append(
                create_evidence(
                    source=EvidenceSource.CLASSIFICATION,
                    category=EvidenceCategory.CONFIDENCE,
                    signal="contract_classification",
                    severity=EvidenceSeverity.INFO,
                    score=Decimal("0.00"),
                    confidence=ConfidenceLevel.MEDIUM,
                    reason=f"Contract classified as {findings.contract_type.value}",
                    metadata={
                        EvidenceMetadataKey.CONFIDENCE_WEIGHT.value: CONFIDENCE_CLASSIFICATION,
                        EvidenceMetadataKey.SIGNAL.value: "contract_classification",
                    },
                )
            )
        if findings.is_contract:
            evidence.append(
                create_evidence(
                    source=EvidenceSource.CLASSIFICATION,
                    category=EvidenceCategory.CONFIDENCE,
                    signal="bytecode_confirmed",
                    severity=EvidenceSeverity.INFO,
                    score=Decimal("0.00"),
                    confidence=ConfidenceLevel.MEDIUM,
                    reason="Contract bytecode confirmed on-chain",
                    metadata={
                        EvidenceMetadataKey.CONFIDENCE_WEIGHT.value: CONFIDENCE_BYTECODE_CONFIRMED,
                        EvidenceMetadataKey.SIGNAL.value: "bytecode_confirmed",
                    },
                )
            )
        if findings.proxy_type is not None and findings.proxy_type not in {
            ProxyType.NONE,
            ProxyType.UNKNOWN,
        }:
            evidence.append(
                create_evidence(
                    source=EvidenceSource.CLASSIFICATION,
                    category=EvidenceCategory.CONFIDENCE,
                    signal="proxy_classification",
                    severity=EvidenceSeverity.INFO,
                    score=Decimal("0.00"),
                    confidence=ConfidenceLevel.MEDIUM,
                    reason=f"Proxy pattern classified as {findings.proxy_type.value}",
                    metadata={
                        EvidenceMetadataKey.CONFIDENCE_WEIGHT.value: 5,
                        EvidenceMetadataKey.SIGNAL.value: "proxy_classification",
                    },
                )
            )
        if findings.trade_simulated:
            evidence.append(
                create_evidence(
                    source=EvidenceSource.SIMULATION,
                    category=EvidenceCategory.CONFIDENCE,
                    signal="trade_simulated",
                    severity=EvidenceSeverity.INFO,
                    score=Decimal("0.00"),
                    confidence=ConfidenceLevel.HIGH,
                    reason="Trade path simulated on fork",
                    metadata={
                        EvidenceMetadataKey.CONFIDENCE_WEIGHT.value: CONFIDENCE_TRADE_SIMULATED,
                        EvidenceMetadataKey.SIGNAL.value: "trade_simulated",
                    },
                )
            )
        detection_weight = RiskEvidenceBuilder._confidence_from_detection_method(
            findings.detection_method
        )
        if detection_weight:
            evidence.append(
                create_evidence(
                    source=EvidenceSource.CLASSIFICATION,
                    category=EvidenceCategory.CONFIDENCE,
                    signal="detection_method",
                    severity=EvidenceSeverity.INFO,
                    score=Decimal("0.00"),
                    confidence=ConfidenceLevel.MEDIUM,
                    reason="Capability/honeypot detection method recorded",
                    metadata={
                        EvidenceMetadataKey.CONFIDENCE_WEIGHT.value: detection_weight,
                        EvidenceMetadataKey.DETECTION_METHOD.value: (
                            findings.detection_method.value if findings.detection_method else None
                        ),
                        EvidenceMetadataKey.SIGNAL.value: "detection_method",
                    },
                )
            )
        return evidence

    @staticmethod
    def _attack_path_items(attack_paths: list[AttackPathData]) -> list[RiskEvidence]:
        evidence: list[RiskEvidence] = []
        for index, path in enumerate(attack_paths):
            evidence.append(
                create_evidence(
                    source=EvidenceSource.THREAT_SURFACE,
                    category=EvidenceCategory.THREAT,
                    signal=f"attack_path:{index}",
                    severity=EvidenceSeverity.HIGH,
                    score=Decimal("0.00"),
                    confidence=RiskEvidenceBuilder._confidence_from_score(path.confidence),
                    reason=f"Attack path identified: {path.name}",
                    metadata={
                        EvidenceMetadataKey.SIGNAL.value: "attack_path",
                        EvidenceMetadataKey.ATTACK_PATH.value: path.name,
                        "steps": path.steps,
                        "detection_source": path.detection_source,
                    },
                )
            )
        return evidence

    @staticmethod
    def _threat_items(items, model_type, prefix: str) -> list[RiskEvidence]:
        evidence: list[RiskEvidence] = []
        for index, item in enumerate(items):
            label = getattr(item, "label", None) or getattr(item, "name", "unknown")
            evidence.append(
                create_evidence(
                    source=EvidenceSource.THREAT_SURFACE,
                    category=EvidenceCategory.THREAT,
                    signal=f"{prefix}:{index}",
                    severity=EvidenceSeverity.MEDIUM,
                    score=Decimal("0.00"),
                    confidence=RiskEvidenceBuilder._confidence_from_score(item.confidence),
                    reason=f"{prefix.replace('_', ' ').title()}: {label}",
                    metadata={
                        EvidenceMetadataKey.SIGNAL.value: prefix,
                        EvidenceMetadataKey.ENTITY_NAME.value: str(label),
                        EvidenceMetadataKey.ENTITY_ADDRESS.value: getattr(item, "address", None),
                        "detection_source": getattr(item, "detection_source", None),
                    },
                )
            )
        return evidence

    @staticmethod
    def _confidence_from_detection_method(
        detection_method: ScanDetectionMethod | None,
    ) -> int:
        if detection_method == ScanDetectionMethod.SOURCE:
            return CONFIDENCE_DETECTION_SOURCE
        if detection_method == ScanDetectionMethod.HYBRID:
            return CONFIDENCE_DETECTION_HYBRID
        if detection_method == ScanDetectionMethod.SIMULATION:
            return CONFIDENCE_DETECTION_SIMULATION
        if detection_method == ScanDetectionMethod.BYTECODE:
            return CONFIDENCE_DETECTION_BYTECODE
        return CONFIDENCE_DETECTION_NONE

    @staticmethod
    def _confidence_from_score(score: int) -> ConfidenceLevel:
        if score >= 75:
            return ConfidenceLevel.HIGH
        if score >= 45:
            return ConfidenceLevel.MEDIUM
        return ConfidenceLevel.LOW

    @staticmethod
    def _severity_for_score(score: Decimal) -> EvidenceSeverity:
        if score >= Decimal("30.00"):
            return EvidenceSeverity.HIGH
        if score >= Decimal("15.00"):
            return EvidenceSeverity.MEDIUM
        if score > Decimal("0.00"):
            return EvidenceSeverity.LOW
        return EvidenceSeverity.INFO
