"""Correlation rule handler protocol (M7.2)."""

from __future__ import annotations

from typing import Protocol

from app.blockchain.risk.correlation.evidence_index import EvidenceIndex
from app.blockchain.risk.correlation.models import CorrelatedRiskFinding, CorrelationRule


class CorrelationRuleHandler(Protocol):
    """Evaluates a registered correlation rule against indexed evidence."""

    @property
    def definition(self) -> CorrelationRule:
        """Return immutable rule metadata."""

    def evaluate(self, index: EvidenceIndex) -> CorrelatedRiskFinding | None:
        """Return a correlated finding when all rule conditions match."""
