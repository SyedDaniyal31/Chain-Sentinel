"""Executive protocol security posture scoring (M8.4)."""

from __future__ import annotations

from decimal import Decimal

from app.blockchain.protocol_report.models import (
    PostureLevel,
    PostureMetric,
    ProtocolIntelligenceAggregate,
    ProtocolSecurityPosture,
    ProtocolStatistics,
)
from app.blockchain.protocol_scheduler.models import NodeScanStatus, ProtocolScanResult
from app.models.enums import AdminType, RiskLevel


class ProtocolScoreCalculator:
    """Derives executive posture metrics from aggregated scan intelligence."""

    def calculate(
        self,
        scan_result: ProtocolScanResult,
        statistics: ProtocolStatistics,
        intelligence: ProtocolIntelligenceAggregate,
    ) -> ProtocolSecurityPosture:
        return ProtocolSecurityPosture(
            protocol_risk=self._protocol_risk(statistics),
            attack_surface=self._attack_surface(intelligence, statistics),
            privilege_concentration=self._privilege_concentration(scan_result, intelligence),
            trust_boundaries=self._trust_boundaries(intelligence),
            dependency_count=self._dependency_count(scan_result, intelligence),
            upgradeability=self._upgradeability(scan_result, statistics),
            governance_maturity=self._governance_maturity(intelligence, statistics),
            protocol_complexity=self._protocol_complexity(statistics, intelligence),
        )

    @staticmethod
    def _protocol_risk(statistics: ProtocolStatistics) -> PostureMetric:
        score = statistics.highest_node_risk_score
        level = _score_to_posture_level(score)
        return PostureMetric(
            name="protocol_risk",
            score=score,
            level=level,
            detail=(
                f"Highest observed node risk score is {score} "
                f"across {statistics.completed_nodes} completed scans"
            ),
        )

    @staticmethod
    def _attack_surface(
        intelligence: ProtocolIntelligenceAggregate,
        statistics: ProtocolStatistics,
    ) -> PostureMetric:
        threat = intelligence.threat
        raw = (
            threat.external_dependency_count * 8
            + threat.attack_path_count * 12
            + threat.critical_asset_count * 10
            + statistics.integration_count * 4
        )
        score = _clamp_score(Decimal(raw))
        return PostureMetric(
            name="attack_surface",
            score=score,
            level=_score_to_posture_level(score),
            detail=(
                f"{threat.external_dependency_count} external dependencies, "
                f"{threat.attack_path_count} attack paths, "
                f"{statistics.integration_count} integrations"
            ),
        )

    @staticmethod
    def _privilege_concentration(
        scan_result: ProtocolScanResult,
        intelligence: ProtocolIntelligenceAggregate,
    ) -> PostureMetric:
        eoa_admin_count = 0
        multisig_admin_count = 0
        for result in scan_result.node_results:
            if result.status != NodeScanStatus.COMPLETED or result.analysis is None:
                continue
            analysis = result.analysis
            if analysis.admin_type == AdminType.EOA:
                eoa_admin_count += 1
            if analysis.admin_type == AdminType.MULTISIG:
                multisig_admin_count += 1

        raw = (
            intelligence.governance.admin_addresses.__len__() * 10
            + intelligence.threat.privileged_entity_count * 8
            + eoa_admin_count * 20
            - multisig_admin_count * 5
        )
        score = _clamp_score(Decimal(max(raw, 0)))
        return PostureMetric(
            name="privilege_concentration",
            score=score,
            level=_score_to_posture_level(score),
            detail=(
                f"{len(intelligence.governance.admin_addresses)} admin address(es), "
                f"{intelligence.threat.privileged_entity_count} privileged entities, "
                f"{eoa_admin_count} EOA admin(s)"
            ),
        )

    @staticmethod
    def _trust_boundaries(intelligence: ProtocolIntelligenceAggregate) -> PostureMetric:
        count = intelligence.threat.trust_boundary_count
        score = _clamp_score(Decimal(count * 15))
        return PostureMetric(
            name="trust_boundaries",
            score=score,
            level=_score_to_posture_level(score),
            detail=f"{count} trust boundaries mapped across scanned contracts",
        )

    @staticmethod
    def _dependency_count(
        scan_result: ProtocolScanResult,
        intelligence: ProtocolIntelligenceAggregate,
    ) -> int:
        batch_dependencies = 0
        if len(scan_result.execution_batches) > 1:
            batch_dependencies = sum(
                len(batch.addresses) for batch in scan_result.execution_batches[1:]
            )
        return max(batch_dependencies, intelligence.relationship.relationship_count)

    @staticmethod
    def _upgradeability(
        scan_result: ProtocolScanResult,
        statistics: ProtocolStatistics,
    ) -> PostureMetric:
        timelock_backed = 0
        for result in scan_result.node_results:
            if result.status != NodeScanStatus.COMPLETED or result.analysis is None:
                continue
            if result.analysis.is_upgradeable and result.analysis.is_timelock:
                timelock_backed += 1

        raw = statistics.upgradeable_node_count * 25 - timelock_backed * 10
        score = _clamp_score(Decimal(max(raw, 0)))
        return PostureMetric(
            name="upgradeability",
            score=score,
            level=_score_to_posture_level(score),
            detail=(
                f"{statistics.upgradeable_node_count} upgradeable node(s), "
                f"{timelock_backed} timelock-backed"
            ),
        )

    @staticmethod
    def _governance_maturity(
        intelligence: ProtocolIntelligenceAggregate,
        statistics: ProtocolStatistics,
    ) -> PostureMetric:
        governance = intelligence.governance
        maturity = (
            governance.timelock_count * 20
            + governance.renounced_ownership_count * 15
            + min(governance.total_role_count, 10) * 3
            + statistics.governance_node_count * 5
        )
        penalty = len(governance.admin_addresses) * 5
        score = _clamp_score(Decimal(max(maturity - penalty, 0)))
        inverted = Decimal("100.00") - score
        level = _score_to_posture_level(inverted)
        return PostureMetric(
            name="governance_maturity",
            score=inverted,
            level=level,
            detail=(
                f"{governance.timelock_count} timelock(s), "
                f"{governance.renounced_ownership_count} renounced ownership record(s), "
                f"{governance.total_role_count} governance roles"
            ),
        )

    @staticmethod
    def _protocol_complexity(
        statistics: ProtocolStatistics,
        intelligence: ProtocolIntelligenceAggregate,
    ) -> PostureMetric:
        raw = (
            statistics.total_nodes * 8
            + statistics.relationship_count * 6
            + statistics.integration_count * 4
            + intelligence.protocol.dex_count * 3
            + intelligence.protocol.oracle_count * 3
        )
        score = _clamp_score(Decimal(raw))
        return PostureMetric(
            name="protocol_complexity",
            score=score,
            level=_score_to_posture_level(score),
            detail=(
                f"{statistics.total_nodes} nodes, "
                f"{statistics.relationship_count} relationships, "
                f"{statistics.integration_count} integrations"
            ),
        )


def overall_protocol_risk(
    statistics: ProtocolStatistics,
    posture: ProtocolSecurityPosture,
) -> tuple[Decimal, str]:
    """Compute aggregate protocol risk score and level from posture metrics."""
    weighted = (
        posture.protocol_risk.score * Decimal("0.35")
        + posture.attack_surface.score * Decimal("0.20")
        + posture.privilege_concentration.score * Decimal("0.15")
        + posture.upgradeability.score * Decimal("0.15")
        + (Decimal("100.00") - posture.governance_maturity.score) * Decimal("0.15")
    )
    score = _clamp_score(weighted.quantize(Decimal("0.01")))
    level = _risk_level_from_score(score)
    if statistics.failed_nodes and level == RiskLevel.LOW.value:
        level = RiskLevel.MEDIUM.value
    return score, level


def _clamp_score(value: Decimal) -> Decimal:
    if value < Decimal("0.00"):
        return Decimal("0.00")
    if value > Decimal("100.00"):
        return Decimal("100.00")
    return value


def _score_to_posture_level(score: Decimal) -> PostureLevel:
    if score >= Decimal("75.00"):
        return PostureLevel.CRITICAL
    if score >= Decimal("50.00"):
        return PostureLevel.HIGH
    if score >= Decimal("25.00"):
        return PostureLevel.MEDIUM
    return PostureLevel.LOW


def _risk_level_from_score(score: Decimal) -> str:
    if score >= Decimal("50.00"):
        return RiskLevel.HIGH.value
    if score >= Decimal("25.00"):
        return RiskLevel.MEDIUM.value
    return RiskLevel.LOW.value
