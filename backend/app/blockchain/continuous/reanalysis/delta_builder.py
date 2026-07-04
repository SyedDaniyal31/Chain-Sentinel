"""Risk evidence delta computation (M10.3)."""

from __future__ import annotations

from app.blockchain.continuous.reanalysis.models import EvidenceDelta
from app.blockchain.risk.models import RiskEvidence


class DeltaBuilder:
    """Compare previous and new risk evidence after selective re-analysis."""

    def build(
        self,
        previous: tuple[RiskEvidence, ...],
        current: tuple[RiskEvidence, ...],
    ) -> EvidenceDelta:
        previous_index = {item.id: item for item in previous}
        current_index = {item.id: item for item in current}

        added: list[RiskEvidence] = []
        removed: list[RiskEvidence] = []
        updated: list[tuple[RiskEvidence, RiskEvidence]] = []

        for evidence_id, item in sorted(current_index.items()):
            prior = previous_index.get(evidence_id)
            if prior is None:
                added.append(item)
            elif _evidence_changed(prior, item):
                updated.append((prior, item))

        for evidence_id, item in sorted(previous_index.items()):
            if evidence_id not in current_index:
                removed.append(item)

        return EvidenceDelta(
            added=tuple(added),
            removed=tuple(removed),
            updated=tuple(updated),
        )


def _evidence_changed(before: RiskEvidence, after: RiskEvidence) -> bool:
    return (
        before.score != after.score
        or before.severity != after.severity
        or before.confidence != after.confidence
        or before.reason != after.reason
        or before.metadata != after.metadata
    )
