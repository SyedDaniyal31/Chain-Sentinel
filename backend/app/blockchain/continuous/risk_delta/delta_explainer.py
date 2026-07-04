"""Deterministic risk delta explanations (M10.4)."""

from __future__ import annotations

from app.blockchain.continuous.reanalysis.models import EvidenceDelta
from app.blockchain.continuous.risk_delta.models import RiskDeltaExplanation, RiskSummary, RiskTrend
from app.blockchain.continuous.risk_delta.severity_mapper import (
    domains_for_evidence,
    evidence_signal,
    intelligence_domain,
    score_contribution,
)
from app.blockchain.risk.models import RiskEvidence


class DeltaExplainer:
    """Generate deterministic explanations for posture changes."""

    def explain(
        self,
        *,
        trend: RiskTrend,
        previous: RiskSummary,
        current: RiskSummary,
        evidence_delta: EvidenceDelta,
    ) -> RiskDeltaExplanation:
        reasons = self._build_reasons(trend, evidence_delta)
        contributing_ids = self._contributing_ids(evidence_delta)
        affected_domains = self._affected_domains(evidence_delta)
        headline = self._headline(trend, previous, current)
        return RiskDeltaExplanation(
            headline=headline,
            reasons=tuple(reasons),
            contributing_evidence_ids=contributing_ids,
            affected_domains=affected_domains,
            metadata={
                "previous_total_score": str(previous.total_score),
                "current_total_score": str(current.total_score),
                "trend": trend.value,
            },
        )

    def _headline(self, trend: RiskTrend, previous: RiskSummary, current: RiskSummary) -> str:
        if trend == RiskTrend.INCREASED:
            return (
                f"Protocol risk posture increased from {previous.total_score} "
                f"to {current.total_score}"
            )
        if trend == RiskTrend.DECREASED:
            return (
                f"Protocol risk posture decreased from {previous.total_score} "
                f"to {current.total_score}"
            )
        return f"Protocol risk posture unchanged at {current.total_score}"

    def _build_reasons(self, trend: RiskTrend, evidence_delta: EvidenceDelta) -> list[str]:
        reasons: list[str] = []

        for item in evidence_delta.added:
            reasons.append(
                f"Added {intelligence_domain(item.source)} evidence '{evidence_signal(item)}' "
                f"({item.severity.value}, score {score_contribution(item)})"
            )
        for item in evidence_delta.removed:
            reasons.append(
                f"Removed {intelligence_domain(item.source)} evidence '{evidence_signal(item)}' "
                f"({item.severity.value}, score {score_contribution(item)})"
            )
        for before, after in evidence_delta.updated:
            delta = score_contribution(after) - score_contribution(before)
            reasons.append(
                f"Updated {intelligence_domain(after.source)} evidence '{evidence_signal(after)}' "
                f"(score delta {delta})"
            )

        if not reasons and trend == RiskTrend.UNCHANGED:
            reasons.append("No material risk evidence changes detected")

        return sorted(reasons)

    def _contributing_ids(self, evidence_delta: EvidenceDelta) -> tuple[str, ...]:
        ids: list[str] = []
        ids.extend(item.id for item in evidence_delta.added)
        ids.extend(item.id for item in evidence_delta.removed)
        ids.extend(after.id for _, after in evidence_delta.updated)
        return tuple(sorted(set(ids)))

    def _affected_domains(self, evidence_delta: EvidenceDelta) -> tuple[str, ...]:
        changed: list[RiskEvidence] = []
        changed.extend(evidence_delta.added)
        changed.extend(evidence_delta.removed)
        changed.extend(after for _, after in evidence_delta.updated)
        return domains_for_evidence(tuple(changed))
