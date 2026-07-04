"""Protocol intelligence report domain models (M8.4)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any

from app.blockchain.risk.correlation.models import CorrelatedRiskFinding
from app.blockchain.risk.models import RiskEvidence


class RecommendationSeverity(StrEnum):
    """Priority band for protocol remediation guidance."""

    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class PostureLevel(StrEnum):
    """Qualitative posture band for executive metrics."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass(frozen=True, slots=True)
class PostureMetric:
    """Single executive security posture measurement."""

    name: str
    score: Decimal
    level: PostureLevel
    detail: str


@dataclass(frozen=True, slots=True)
class ProtocolRecommendation:
    """Prioritized remediation or review action."""

    id: str
    title: str
    severity: RecommendationSeverity
    priority: int
    rationale: str
    category: str
    affected_nodes: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class ProtocolStatistics:
    """Quantitative protocol scan and coverage statistics."""

    total_nodes: int
    completed_nodes: int
    failed_nodes: int
    skipped_nodes: int
    scan_duration_ms: float
    parallel_batches: int
    evidence_count: int
    correlated_finding_count: int
    highest_node_risk_score: Decimal
    upgradeable_node_count: int
    governance_node_count: int
    integration_count: int
    relationship_count: int
    attack_path_count: int


@dataclass(frozen=True, slots=True)
class ProtocolSecurityPosture:
    """Executive security posture metrics for auditors and operators."""

    protocol_risk: PostureMetric
    attack_surface: PostureMetric
    privilege_concentration: PostureMetric
    trust_boundaries: PostureMetric
    dependency_count: int
    upgradeability: PostureMetric
    governance_maturity: PostureMetric
    protocol_complexity: PostureMetric


@dataclass(frozen=True, slots=True)
class GovernanceIntelligenceSummary:
    """Aggregated governance intelligence across protocol nodes."""

    governance_types: tuple[str, ...]
    upgrade_authorities: tuple[str, ...]
    timelock_count: int
    renounced_ownership_count: int
    total_role_count: int
    admin_addresses: tuple[str, ...]
    nodes: tuple[dict[str, Any], ...]


@dataclass(frozen=True, slots=True)
class LiquidityIntelligenceSummary:
    """Aggregated liquidity intelligence across protocol nodes."""

    nodes_with_liquidity: int
    total_liquidity_usd: Decimal
    locked_pool_count: int
    unlocked_pool_count: int
    primary_dexes: tuple[str, ...]
    nodes: tuple[dict[str, Any], ...]


@dataclass(frozen=True, slots=True)
class WalletIntelligenceSummary:
    """Aggregated wallet intelligence across protocol nodes."""

    flagged_wallet_count: int
    fresh_deployer_count: int
    tornado_funded_count: int
    multisig_treasury_count: int
    highest_wallet_risk_score: int
    nodes: tuple[dict[str, Any], ...]


@dataclass(frozen=True, slots=True)
class ProtocolIntelligenceSummary:
    """Aggregated protocol classification and integration intelligence."""

    protocol_names: tuple[str, ...]
    protocol_families: tuple[str, ...]
    standards: tuple[str, ...]
    integrations: tuple[str, ...]
    dex_count: int
    oracle_count: int
    bridge_count: int
    vault_count: int
    nodes: tuple[dict[str, Any], ...]


@dataclass(frozen=True, slots=True)
class RelationshipIntelligenceSummary:
    """Aggregated cross-contract relationship intelligence."""

    relationship_count: int
    relationship_types: tuple[str, ...]
    edges: tuple[dict[str, Any], ...]


@dataclass(frozen=True, slots=True)
class ThreatIntelligenceSummary:
    """Aggregated threat surface intelligence."""

    external_dependency_count: int
    trust_boundary_count: int
    privileged_entity_count: int
    attack_path_count: int
    critical_asset_count: int
    attack_paths: tuple[str, ...]
    privileged_entities: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CorrelatedEvidenceSummary:
    """Summary of correlated risk findings across the protocol."""

    finding_count: int
    severities: tuple[str, ...]
    findings: tuple[CorrelatedRiskFinding, ...]


@dataclass(frozen=True, slots=True)
class ProtocolIntelligenceAggregate:
    """Protocol-wide intelligence roll-up consumed by the executive report."""

    governance: GovernanceIntelligenceSummary
    liquidity: LiquidityIntelligenceSummary
    wallet: WalletIntelligenceSummary
    protocol: ProtocolIntelligenceSummary
    relationship: RelationshipIntelligenceSummary
    threat: ThreatIntelligenceSummary
    correlated_evidence: CorrelatedEvidenceSummary
    risk_evidence: tuple[RiskEvidence, ...]


@dataclass(frozen=True, slots=True)
class ProtocolSummary:
    """High-level narrative summary for auditors and operators."""

    protocol_root: str
    protocol_name: str
    headline: str
    overview: str
    overall_risk_level: str
    overall_risk_score: Decimal
    key_findings: tuple[str, ...]
    scan_coverage_pct: Decimal
    generated_at: datetime


@dataclass(frozen=True, slots=True)
class ProtocolExecutiveReport:
    """Deterministic executive protocol security assessment."""

    report_id: str
    summary: ProtocolSummary
    statistics: ProtocolStatistics
    posture: ProtocolSecurityPosture
    intelligence: ProtocolIntelligenceAggregate
    recommendations: tuple[ProtocolRecommendation, ...]
    node_risk_table: tuple[dict[str, Any], ...]
    metadata: dict[str, Any] = field(default_factory=dict)
