"""Risk delta computation engine (M10.4)."""

from __future__ import annotations

from app.blockchain.continuous.reanalysis.models import EvidenceDelta
from app.blockchain.continuous.risk_delta.delta_classifier import DeltaClassifier
from app.blockchain.continuous.risk_delta.delta_explainer import DeltaExplainer
from app.blockchain.continuous.risk_delta.models import (
    EvidenceSummary,
    RiskDelta,
    RiskDeltaReport,
    RiskEvidenceBundle,
    RiskSummary,
    RiskTrend,
)
from app.blockchain.continuous.risk_delta.severity_mapper import evidence_signal, summarize_bundle


class RiskDeltaEngine:
    """Compute explainable risk posture deltas from evidence changes."""

    def __init__(
        self,
        classifier: DeltaClassifier | None = None,
        explainer: DeltaExplainer | None = None,
    ) -> None:
        self._classifier = classifier or DeltaClassifier()
        self._explainer = explainer or DeltaExplainer()

    def compute(
        self,
        evidence_delta: EvidenceDelta,
        previous: RiskEvidenceBundle,
        current: RiskEvidenceBundle,
    ) -> RiskDeltaReport:
        if previous.watch_id != current.watch_id:
            raise ValueError("previous and current bundles must share the same watch_id")

        previous_summary = summarize_bundle(previous)
        current_summary = summarize_bundle(current)
        score_delta = self._classifier.score_delta(previous_summary, current_summary, evidence_delta)
        trend = self._classifier.classify(previous_summary, current_summary, evidence_delta)
        explanation = self._explainer.explain(
            trend=trend,
            previous=previous_summary,
            current=current_summary,
            evidence_delta=evidence_delta,
        )
        delta = RiskDelta(
            watch_id=previous.watch_id,
            previous_summary=previous_summary,
            current_summary=current_summary,
            score_delta=score_delta,
            added=evidence_delta.added,
            removed=evidence_delta.removed,
            updated=evidence_delta.updated,
            trend=trend,
        )
        return RiskDeltaReport(
            watch_id=previous.watch_id,
            delta=delta,
            previous_summary=previous_summary,
            current_summary=current_summary,
            trend=trend,
            explanation=explanation,
            evidence_summary=_build_evidence_summary(evidence_delta),
        )


def _build_evidence_summary(evidence_delta: EvidenceDelta) -> EvidenceSummary:
    signals: list[str] = []
    signals.extend(evidence_signal(item) for item in evidence_delta.added)
    signals.extend(evidence_signal(item) for item in evidence_delta.removed)
    signals.extend(evidence_signal(after) for _, after in evidence_delta.updated)

    from app.blockchain.continuous.risk_delta.severity_mapper import domains_for_evidence

    changed = evidence_delta.added + evidence_delta.removed + tuple(
        after for _, after in evidence_delta.updated
    )
    return EvidenceSummary(
        added_count=len(evidence_delta.added),
        removed_count=len(evidence_delta.removed),
        updated_count=len(evidence_delta.updated),
        affected_domains=domains_for_evidence(changed),
        contributing_signals=tuple(sorted(set(signals))),
    )
