"""Correlation domain models (M7.2)."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import StrEnum
from typing import Any

from app.blockchain.risk.evidence_types import EvidenceSeverity
from app.models.enums import ConfidenceLevel


class CorrelationImpact(StrEnum):
    """Estimated impact if the correlated pattern is exploited."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class CorrelationLikelihood(StrEnum):
    """Estimated likelihood of the correlated pattern materializing."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class CorrelationFindingMetadataKey(StrEnum):
    """Well-known metadata keys on correlated findings."""

    THREAT_WEIGHT = "threat_weight"
    CENTRALIZATION_WEIGHT = "centralization_weight"
    FORCE_THREAT_CRITICAL = "force_threat_critical"


@dataclass(frozen=True, slots=True)
class CorrelationRule:
    """Immutable correlation rule definition registered in the rule registry."""

    id: str
    title: str
    description: str
    severity: EvidenceSeverity
    impact: CorrelationImpact
    likelihood: CorrelationLikelihood
    score_delta: Decimal
    priority: int = 100


@dataclass(frozen=True, slots=True)
class CorrelatedRiskFinding:
    """Higher-level security finding produced by correlating multiple evidence items."""

    id: str
    title: str
    description: str
    severity: EvidenceSeverity
    confidence: ConfidenceLevel
    score_delta: Decimal
    impact: CorrelationImpact
    likelihood: CorrelationLikelihood
    explanation: str
    evidence_ids: tuple[str, ...]
    correlation_rule: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class CorrelationResult:
    """Output of a correlation pass over normalized risk evidence."""

    findings: tuple[CorrelatedRiskFinding, ...]
    evidence_count: int
    rules_evaluated: int
