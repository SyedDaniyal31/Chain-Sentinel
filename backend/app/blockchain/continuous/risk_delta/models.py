"""Risk delta domain models (M10.4)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any

from app.blockchain.risk.evidence_types import EvidenceSeverity
from app.blockchain.risk.models import RiskEvidence


class RiskTrend(StrEnum):
    """Direction of protocol security posture change."""

    INCREASED = "increased"
    DECREASED = "decreased"
    UNCHANGED = "unchanged"


@dataclass(frozen=True, slots=True)
class RiskEvidenceBundle:
    """Snapshot of normalized risk evidence for posture comparison (M10.4)."""

    watch_id: str
    evidence: tuple[RiskEvidence, ...]
    captured_at: datetime


@dataclass(frozen=True, slots=True)
class RiskSummary:
    """Aggregated risk posture summary derived from evidence."""

    watch_id: str
    total_score: Decimal
    evidence_count: int
    max_severity: EvidenceSeverity
    severity_counts: tuple[tuple[str, int], ...]
    intelligence_domains: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RiskDelta:
    """Immutable posture delta between previous and current evidence states."""

    watch_id: str
    previous_summary: RiskSummary
    current_summary: RiskSummary
    score_delta: Decimal
    added: tuple[RiskEvidence, ...]
    removed: tuple[RiskEvidence, ...]
    updated: tuple[tuple[RiskEvidence, RiskEvidence], ...]
    trend: RiskTrend


@dataclass(frozen=True, slots=True)
class RiskDeltaExplanation:
    """Deterministic explanation of posture change."""

    headline: str
    reasons: tuple[str, ...]
    contributing_evidence_ids: tuple[str, ...]
    affected_domains: tuple[str, ...]
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class EvidenceSummary:
    """Aggregate summary of evidence changes contributing to the delta."""

    added_count: int
    removed_count: int
    updated_count: int
    affected_domains: tuple[str, ...]
    contributing_signals: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RiskDeltaReport:
    """Complete output of risk delta analysis."""

    watch_id: str
    delta: RiskDelta
    previous_summary: RiskSummary
    current_summary: RiskSummary
    trend: RiskTrend
    explanation: RiskDeltaExplanation
    evidence_summary: EvidenceSummary
