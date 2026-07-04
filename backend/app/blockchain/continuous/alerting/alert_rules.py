"""Alert generation rules (M10.5)."""

from __future__ import annotations

from decimal import Decimal

from app.blockchain.continuous.alerting.models import AlertAcknowledgementState, AlertRuleType, SecurityAlert
from app.blockchain.continuous.risk_delta.models import RiskDeltaReport, RiskTrend
from app.blockchain.continuous.risk_delta.severity_mapper import evidence_signal, intelligence_domain
from app.blockchain.risk.evidence_types import EvidenceMetadataKey, EvidenceSeverity, EvidenceSource
from app.blockchain.risk.models import RiskEvidence

GOVERNANCE_SIGNALS = frozenset({"owner_changed", "admin_authority", "proxyadmin_owner"})
IMPLEMENTATION_SIGNALS = frozenset(
    {"implementation_changed", "upgradeable", "implementation_exposed", "proxy_execution"}
)
OWNERSHIP_SIGNALS = frozenset({"owner_changed", "ownership_capability", "proxyadmin_owner"})
TREASURY_SIGNALS = frozenset({"treasury_multisig", "treasury_change"})
RUNTIME_SIGNALS = frozenset(
    {
        "runtime_exploit",
        "runtime_selfdestruct",
        "delegatecall_chain",
        "unexpected_external_call",
        "flash_loan_callback",
        "state_transition_observed",
    }
)

HIGH_SCORE_DELTA = Decimal("20.00")
CRITICAL_SCORE_DELTA = Decimal("40.00")


class AlertRuleEngine:
    """Generate candidate alerts from a risk delta report."""

    def evaluate(self, report: RiskDeltaReport, *, generated_at: object) -> list[SecurityAlert]:
        candidates: list[SecurityAlert] = []
        candidates.extend(self._risk_increase_rules(report, generated_at=generated_at))
        candidates.extend(self._evidence_rules(report, generated_at=generated_at))
        return candidates

    def _risk_increase_rules(self, report: RiskDeltaReport, *, generated_at: object) -> list[SecurityAlert]:
        if report.trend != RiskTrend.INCREASED:
            return []

        alerts: list[SecurityAlert] = []
        if report.delta.score_delta >= CRITICAL_SCORE_DELTA or report.current_summary.max_severity == EvidenceSeverity.CRITICAL:
            alerts.append(
                _build_alert(
                    report,
                    rule_type=AlertRuleType.CRITICAL_RISK_INCREASE,
                    severity=EvidenceSeverity.CRITICAL,
                    title="Critical risk posture increase detected",
                    summary=report.explanation.headline,
                    evidence_ids=report.explanation.contributing_evidence_ids,
                    generated_at=generated_at,
                )
            )
        elif report.delta.score_delta >= HIGH_SCORE_DELTA or report.current_summary.max_severity == EvidenceSeverity.HIGH:
            alerts.append(
                _build_alert(
                    report,
                    rule_type=AlertRuleType.HIGH_RISK_INCREASE,
                    severity=EvidenceSeverity.HIGH,
                    title="High risk posture increase detected",
                    summary=report.explanation.headline,
                    evidence_ids=report.explanation.contributing_evidence_ids,
                    generated_at=generated_at,
                )
            )
        return alerts

    def _evidence_rules(self, report: RiskDeltaReport, *, generated_at: object) -> list[SecurityAlert]:
        alerts: list[SecurityAlert] = []
        for evidence in report.delta.added:
            alerts.extend(self._rules_for_added_evidence(report, evidence, generated_at=generated_at))
        for before, after in report.delta.updated:
            alerts.extend(
                self._rules_for_updated_evidence(report, before, after, generated_at=generated_at)
            )
        return alerts

    def _rules_for_added_evidence(
        self,
        report: RiskDeltaReport,
        evidence: RiskEvidence,
        *,
        generated_at: object,
    ) -> list[SecurityAlert]:
        alerts: list[SecurityAlert] = []
        signal = evidence_signal(evidence)

        if evidence.severity == EvidenceSeverity.CRITICAL:
            alerts.append(
                _build_alert(
                    report,
                    rule_type=AlertRuleType.NEW_CRITICAL_EVIDENCE,
                    severity=EvidenceSeverity.CRITICAL,
                    title=f"New critical evidence detected: {signal}",
                    summary=evidence.reason,
                    evidence_ids=(evidence.id,),
                    generated_at=generated_at,
                )
            )

        if _matches(signal, GOVERNANCE_SIGNALS) or intelligence_domain(evidence.source) == "governance":
            alerts.append(
                _build_alert(
                    report,
                    rule_type=AlertRuleType.GOVERNANCE_CHANGE,
                    severity=max_severity(evidence.severity, EvidenceSeverity.HIGH),
                    title="Governance change detected",
                    summary=evidence.reason,
                    evidence_ids=(evidence.id,),
                    generated_at=generated_at,
                )
            )

        if _matches(signal, IMPLEMENTATION_SIGNALS) or evidence.source == EvidenceSource.PROXY:
            alerts.append(
                _build_alert(
                    report,
                    rule_type=AlertRuleType.IMPLEMENTATION_CHANGE,
                    severity=max_severity(evidence.severity, EvidenceSeverity.CRITICAL),
                    title="Implementation change detected",
                    summary=evidence.reason,
                    evidence_ids=(evidence.id,),
                    generated_at=generated_at,
                )
            )

        if _matches(signal, OWNERSHIP_SIGNALS):
            alerts.append(
                _build_alert(
                    report,
                    rule_type=AlertRuleType.OWNERSHIP_CHANGE,
                    severity=max_severity(evidence.severity, EvidenceSeverity.HIGH),
                    title="Ownership change detected",
                    summary=evidence.reason,
                    evidence_ids=(evidence.id,),
                    generated_at=generated_at,
                )
            )

        if _matches(signal, TREASURY_SIGNALS) or "treasury" in signal:
            alerts.append(
                _build_alert(
                    report,
                    rule_type=AlertRuleType.TREASURY_CHANGE,
                    severity=max_severity(evidence.severity, EvidenceSeverity.HIGH),
                    title="Treasury change detected",
                    summary=evidence.reason,
                    evidence_ids=(evidence.id,),
                    generated_at=generated_at,
                )
            )

        if _matches(signal, RUNTIME_SIGNALS) or evidence.source in {
            EvidenceSource.SIMULATION,
            EvidenceSource.THREAT_SURFACE,
            EvidenceSource.CLASSIFICATION,
        }:
            alerts.append(
                _build_alert(
                    report,
                    rule_type=AlertRuleType.RUNTIME_EXPLOIT_INDICATOR,
                    severity=max_severity(evidence.severity, EvidenceSeverity.HIGH),
                    title="Runtime exploit indicator detected",
                    summary=evidence.reason,
                    evidence_ids=(evidence.id,),
                    generated_at=generated_at,
                )
            )

        return alerts

    def _rules_for_updated_evidence(
        self,
        report: RiskDeltaReport,
        before: RiskEvidence,
        after: RiskEvidence,
        *,
        generated_at: object,
    ) -> list[SecurityAlert]:
        if after.severity != EvidenceSeverity.CRITICAL:
            return []
        if before.severity == EvidenceSeverity.CRITICAL:
            return []
        return [
            _build_alert(
                report,
                rule_type=AlertRuleType.NEW_CRITICAL_EVIDENCE,
                severity=EvidenceSeverity.CRITICAL,
                title=f"Evidence escalated to critical: {evidence_signal(after)}",
                summary=after.reason,
                evidence_ids=(after.id,),
                generated_at=generated_at,
            )
        ]


def _build_alert(
    report: RiskDeltaReport,
    *,
    rule_type: AlertRuleType,
    severity: EvidenceSeverity,
    title: str,
    summary: str,
    evidence_ids: tuple[str, ...],
    generated_at: object,
) -> SecurityAlert:
    from app.blockchain.continuous.alerting.deduplicator import build_alert_id

    protocol, contracts = _protocol_context(report)
    alert_id = build_alert_id(
        watch_id=report.watch_id,
        rule_type=rule_type,
        evidence_ids=evidence_ids,
    )
    return SecurityAlert(
        alert_id=alert_id,
        severity=severity,
        title=title,
        summary=summary,
        affected_protocol=protocol,
        affected_contracts=contracts,
        evidence_references=evidence_ids,
        timestamp=generated_at,  # type: ignore[arg-type]
        acknowledgement_state=AlertAcknowledgementState.PENDING,
        rule_type=rule_type,
        metadata={
            "watch_id": report.watch_id,
            "trend": report.trend.value,
            "score_delta": str(report.delta.score_delta),
        },
    )


def _protocol_context(report: RiskDeltaReport) -> tuple[str, tuple[str, ...]]:
    watch_id = report.watch_id
    if ":" in watch_id:
        _, address = watch_id.split(":", 1)
        return watch_id, (address.lower(),)
    return watch_id, ()


def _matches(signal: str, candidates: frozenset[str]) -> bool:
    normalized = signal.lower()
    return normalized in candidates or any(token in normalized for token in candidates)


def max_severity(current: EvidenceSeverity, minimum: EvidenceSeverity) -> EvidenceSeverity:
    order = [
        EvidenceSeverity.INFO,
        EvidenceSeverity.LOW,
        EvidenceSeverity.MEDIUM,
        EvidenceSeverity.HIGH,
        EvidenceSeverity.CRITICAL,
    ]
    return order[max(order.index(current), order.index(minimum))]
