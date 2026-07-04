"""Risk posture trend classification (M10.4)."""

from __future__ import annotations

from decimal import Decimal

from app.blockchain.continuous.reanalysis.models import EvidenceDelta
from app.blockchain.continuous.risk_delta.models import RiskSummary, RiskTrend
from app.blockchain.continuous.risk_delta.severity_mapper import score_contribution


class DeltaClassifier:
    """Classify posture trend from summaries and evidence delta."""

    def classify(
        self,
        previous: RiskSummary,
        current: RiskSummary,
        evidence_delta: EvidenceDelta,
    ) -> RiskTrend:
        score_delta = self.score_delta(previous, current, evidence_delta)
        if score_delta > Decimal("0.00"):
            return RiskTrend.INCREASED
        if score_delta < Decimal("0.00"):
            return RiskTrend.DECREASED
        if self._has_material_changes(evidence_delta):
            return RiskTrend.UNCHANGED
        return RiskTrend.UNCHANGED

    def score_delta(
        self,
        previous: RiskSummary,
        current: RiskSummary,
        evidence_delta: EvidenceDelta,
    ) -> Decimal:
        added = sum(score_contribution(item) for item in evidence_delta.added)
        removed = sum(score_contribution(item) for item in evidence_delta.removed)
        updated = sum(
            score_contribution(after) - score_contribution(before)
            for before, after in evidence_delta.updated
        )
        computed = added - removed + updated
        summary_delta = current.total_score - previous.total_score
        if computed == summary_delta:
            return computed
        return summary_delta

    def _has_material_changes(self, evidence_delta: EvidenceDelta) -> bool:
        return bool(evidence_delta.added or evidence_delta.removed or evidence_delta.updated)
