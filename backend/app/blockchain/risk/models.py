"""Risk evidence domain models (M7.1)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from app.blockchain.risk.evidence_types import EvidenceCategory, EvidenceSeverity, EvidenceSource
from app.models.enums import ConfidenceLevel


@dataclass(frozen=True, slots=True)
class RiskEvidence:
    """Normalized risk signal emitted by analyzers and consumed by RiskEngine."""

    id: str
    source: EvidenceSource
    category: EvidenceCategory
    severity: EvidenceSeverity
    score: Decimal
    confidence: ConfidenceLevel
    reason: str
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
