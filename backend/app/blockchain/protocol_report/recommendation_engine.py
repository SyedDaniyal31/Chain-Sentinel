"""Protocol recommendation generation from scan evidence (M8.4)."""

from __future__ import annotations

from decimal import Decimal

from app.blockchain.protocol_report.models import (
    ProtocolIntelligenceAggregate,
    ProtocolRecommendation,
    ProtocolStatistics,
    RecommendationSeverity,
)
from app.blockchain.protocol_scheduler.models import NodeScanStatus, ProtocolScanResult
from app.blockchain.risk.evidence_types import EvidenceSeverity
from app.models.enums import AdminType, RiskLevel


class RecommendationEngine:
    """Converts normalized evidence into prioritized protocol recommendations."""

    def generate(
        self,
        scan_result: ProtocolScanResult,
        statistics: ProtocolStatistics,
        intelligence: ProtocolIntelligenceAggregate,
    ) -> tuple[ProtocolRecommendation, ...]:
        recommendations: list[ProtocolRecommendation] = []

        recommendations.extend(self._coverage_recommendations(scan_result, statistics))
        recommendations.extend(self._node_risk_recommendations(scan_result))
        recommendations.extend(self._upgradeability_recommendations(scan_result))
        recommendations.extend(self._governance_recommendations(intelligence))
        recommendations.extend(self._wallet_recommendations(scan_result, intelligence))
        recommendations.extend(self._liquidity_recommendations(scan_result))
        recommendations.extend(self._threat_recommendations(intelligence))
        recommendations.extend(self._correlation_recommendations(intelligence))

        return tuple(sorted(recommendations, key=_recommendation_sort_key))

    @staticmethod
    def _coverage_recommendations(
        scan_result: ProtocolScanResult,
        statistics: ProtocolStatistics,
    ) -> list[ProtocolRecommendation]:
        recommendations: list[ProtocolRecommendation] = []
        if statistics.failed_nodes:
            failed = tuple(sorted(scan_result.failed_nodes))
            recommendations.append(
                ProtocolRecommendation(
                    id="coverage.failed_scans",
                    title="Re-run failed contract scans",
                    severity=RecommendationSeverity.MEDIUM,
                    priority=200,
                    rationale=(
                        f"{statistics.failed_nodes} contract scan(s) failed, leaving gaps "
                        "in protocol coverage."
                    ),
                    category="coverage",
                    affected_nodes=failed,
                )
            )
        if statistics.skipped_nodes:
            skipped = tuple(
                sorted(
                    result.address
                    for result in scan_result.node_results
                    if result.status == NodeScanStatus.SKIPPED
                )
            )
            recommendations.append(
                ProtocolRecommendation(
                    id="coverage.skipped_nodes",
                    title="Review dependency-blocked contracts",
                    severity=RecommendationSeverity.MEDIUM,
                    priority=210,
                    rationale=(
                        f"{statistics.skipped_nodes} contract(s) were skipped because "
                        "upstream dependencies failed or remained unresolved."
                    ),
                    category="coverage",
                    affected_nodes=skipped,
                )
            )
        return recommendations

    @staticmethod
    def _node_risk_recommendations(
        scan_result: ProtocolScanResult,
    ) -> list[ProtocolRecommendation]:
        recommendations: list[ProtocolRecommendation] = []
        for result in scan_result.node_results:
            if result.status != NodeScanStatus.COMPLETED or result.analysis is None:
                continue
            if result.analysis.risk_level == RiskLevel.HIGH or result.analysis.risk_score >= Decimal(
                "50.00"
            ):
                recommendations.append(
                    ProtocolRecommendation(
                        id=f"risk.high_node.{result.address}",
                        title="Review high-risk contract",
                        severity=RecommendationSeverity.HIGH,
                        priority=100,
                        rationale=(
                            f"Contract risk score {result.analysis.risk_score} "
                            f"({result.analysis.risk_level.value})."
                        ),
                        category="risk",
                        affected_nodes=(result.address,),
                    )
                )
        return recommendations

    @staticmethod
    def _upgradeability_recommendations(
        scan_result: ProtocolScanResult,
    ) -> list[ProtocolRecommendation]:
        recommendations: list[ProtocolRecommendation] = []
        for result in scan_result.node_results:
            if result.status != NodeScanStatus.COMPLETED or result.analysis is None:
                continue
            analysis = result.analysis
            if not analysis.is_upgradeable:
                continue
            if analysis.is_timelock:
                continue
            severity = RecommendationSeverity.HIGH
            if analysis.admin_type == AdminType.EOA:
                severity = RecommendationSeverity.CRITICAL
            recommendations.append(
                ProtocolRecommendation(
                    id=f"upgrade.unprotected.{result.address}",
                    title="Constrain upgrade authority",
                    severity=severity,
                    priority=50 if severity == RecommendationSeverity.CRITICAL else 80,
                    rationale=(
                        "Upgradeable contract without timelock protection increases "
                        "instant governance takeover risk."
                    ),
                    category="upgradeability",
                    affected_nodes=(result.address,),
                )
            )
        return recommendations

    @staticmethod
    def _governance_recommendations(
        intelligence: ProtocolIntelligenceAggregate,
    ) -> list[ProtocolRecommendation]:
        recommendations: list[ProtocolRecommendation] = []
        if intelligence.governance.admin_addresses and not intelligence.governance.timelock_count:
            recommendations.append(
                ProtocolRecommendation(
                    id="governance.no_timelock",
                    title="Introduce governance timelock",
                    severity=RecommendationSeverity.HIGH,
                    priority=70,
                    rationale=(
                        "Administrative control exists without a detected timelock delay "
                        "on upgradeable components."
                    ),
                    category="governance",
                    affected_nodes=intelligence.governance.admin_addresses,
                )
            )
        return recommendations

    @staticmethod
    def _wallet_recommendations(
        scan_result: ProtocolScanResult,
        intelligence: ProtocolIntelligenceAggregate,
    ) -> list[ProtocolRecommendation]:
        recommendations: list[ProtocolRecommendation] = []
        if intelligence.wallet.flagged_wallet_count:
            affected = tuple(
                sorted(
                    result.address
                    for result in scan_result.node_results
                    if result.status == NodeScanStatus.COMPLETED
                    and result.analysis
                    and result.analysis.wallet_reputation_known_scam
                )
            )
            recommendations.append(
                ProtocolRecommendation(
                    id="wallet.known_scam",
                    title="Investigate scam-associated wallets",
                    severity=RecommendationSeverity.CRITICAL,
                    priority=10,
                    rationale=(
                        "One or more scanned contracts are linked to wallets flagged "
                        "as known scams."
                    ),
                    category="wallet",
                    affected_nodes=affected,
                )
            )
        if intelligence.wallet.tornado_funded_count:
            affected = tuple(
                sorted(
                    result.address
                    for result in scan_result.node_results
                    if result.status == NodeScanStatus.COMPLETED
                    and result.analysis
                    and result.analysis.wallet_tornado_funded_deployer
                )
            )
            recommendations.append(
                ProtocolRecommendation(
                    id="wallet.tornado_funded",
                    title="Review tornado-funded deployer lineage",
                    severity=RecommendationSeverity.HIGH,
                    priority=60,
                    rationale=(
                        "Deployer funding traces to a tornado-style privacy mixer, "
                        "increasing obfuscation risk."
                    ),
                    category="wallet",
                    affected_nodes=affected,
                )
            )
        return recommendations

    @staticmethod
    def _liquidity_recommendations(
        scan_result: ProtocolScanResult,
    ) -> list[ProtocolRecommendation]:
        recommendations: list[ProtocolRecommendation] = []
        for result in scan_result.node_results:
            if result.status != NodeScanStatus.COMPLETED or result.analysis is None:
                continue
            analysis = result.analysis
            if analysis.liquidity_has_liquidity and not analysis.liquidity_locked:
                recommendations.append(
                    ProtocolRecommendation(
                        id=f"liquidity.unlocked.{result.address}",
                        title="Review unlocked liquidity ownership",
                        severity=RecommendationSeverity.HIGH,
                        priority=90,
                        rationale=(
                            "Liquidity is present but not locked, increasing rug-pull "
                            "and exit-scam exposure."
                        ),
                        category="liquidity",
                        affected_nodes=(result.address,),
                    )
                )
        return recommendations

    @staticmethod
    def _threat_recommendations(
        intelligence: ProtocolIntelligenceAggregate,
    ) -> list[ProtocolRecommendation]:
        recommendations: list[ProtocolRecommendation] = []
        if intelligence.threat.attack_path_count:
            recommendations.append(
                ProtocolRecommendation(
                    id="threat.attack_paths",
                    title="Validate inferred attack paths",
                    severity=RecommendationSeverity.MEDIUM,
                    priority=120,
                    rationale=(
                        f"{intelligence.threat.attack_path_count} attack path(s) were "
                        "inferred across the protocol threat surface."
                    ),
                    category="threat",
                    affected_nodes=(),
                )
            )
        return recommendations

    @staticmethod
    def _correlation_recommendations(
        intelligence: ProtocolIntelligenceAggregate,
    ) -> list[ProtocolRecommendation]:
        recommendations: list[ProtocolRecommendation] = []
        for index, finding in enumerate(intelligence.correlated_evidence.findings):
            severity = _map_evidence_severity(finding.severity)
            recommendations.append(
                ProtocolRecommendation(
                    id=f"correlation.{finding.correlation_rule}.{index}",
                    title=finding.title,
                    severity=severity,
                    priority=40 if severity == RecommendationSeverity.CRITICAL else 110,
                    rationale=finding.explanation or finding.description,
                    category="correlation",
                    affected_nodes=(),
                )
            )
        return recommendations


def _map_evidence_severity(severity: EvidenceSeverity) -> RecommendationSeverity:
    mapping = {
        EvidenceSeverity.INFO: RecommendationSeverity.INFO,
        EvidenceSeverity.LOW: RecommendationSeverity.LOW,
        EvidenceSeverity.MEDIUM: RecommendationSeverity.MEDIUM,
        EvidenceSeverity.HIGH: RecommendationSeverity.HIGH,
        EvidenceSeverity.CRITICAL: RecommendationSeverity.CRITICAL,
    }
    return mapping.get(severity, RecommendationSeverity.MEDIUM)


def _recommendation_sort_key(recommendation: ProtocolRecommendation) -> tuple[int, int, str]:
    severity_rank = {
        RecommendationSeverity.CRITICAL: 0,
        RecommendationSeverity.HIGH: 1,
        RecommendationSeverity.MEDIUM: 2,
        RecommendationSeverity.LOW: 3,
        RecommendationSeverity.INFO: 4,
    }
    return (severity_rank[recommendation.severity], recommendation.priority, recommendation.id)
