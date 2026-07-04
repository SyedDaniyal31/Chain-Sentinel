"""Risk evidence factory helpers (M7.1)."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from app.blockchain.risk.evidence_types import EvidenceCategory, EvidenceSeverity, EvidenceSource
from app.blockchain.risk.models import RiskEvidence
from app.models.enums import ConfidenceLevel


def evidence_id(source: EvidenceSource, category: EvidenceCategory, signal: str) -> str:
    """Build a stable evidence identifier for correlation and deduplication."""
    return f"{source.value}:{category.value}:{signal}"


def create_evidence(
    *,
    source: EvidenceSource,
    category: EvidenceCategory,
    signal: str,
    severity: EvidenceSeverity,
    score: Decimal | int | float = Decimal("0.00"),
    confidence: ConfidenceLevel = ConfidenceLevel.LOW,
    reason: str,
    metadata: dict[str, Any] | None = None,
    timestamp: datetime | None = None,
) -> RiskEvidence:
    """Create a normalized RiskEvidence instance."""
    return RiskEvidence(
        id=evidence_id(source, category, signal),
        source=source,
        category=category,
        severity=severity,
        score=Decimal(str(score)),
        confidence=confidence,
        reason=reason,
        metadata=dict(metadata or {}),
        timestamp=timestamp or datetime.now(UTC),
    )


def merge_evidence(*groups: list[RiskEvidence]) -> list[RiskEvidence]:
    """Concatenate evidence lists while preserving first-seen order by id."""
    merged: list[RiskEvidence] = []
    seen: set[str] = set()
    for group in groups:
        for item in group:
            if item.id in seen:
                continue
            seen.add(item.id)
            merged.append(item)
    return merged
