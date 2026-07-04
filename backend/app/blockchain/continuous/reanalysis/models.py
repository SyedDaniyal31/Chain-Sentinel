"""Selective re-analysis domain models (M10.3)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any

from app.blockchain.continuous.change_detection.models import ChangeDetectionResult, ChangeType
from app.blockchain.risk.models import RiskEvidence


class ReanalysisModule(StrEnum):
    """Existing intelligence modules eligible for selective re-analysis."""

    CAPABILITY = "capability"
    PROTOCOL = "protocol"
    THREAT = "threat"
    GOVERNANCE = "governance"
    LIQUIDITY = "liquidity"
    RELATIONSHIP = "relationship"


@dataclass(frozen=True, slots=True)
class ExecutionPlan:
    """Deterministic plan listing required analyzer modules."""

    plan_id: str
    watch_id: str
    modules: tuple[ReanalysisModule, ...]
    triggered_by: tuple[ChangeType, ...]
    affected_contracts: tuple[str, ...]
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class EvidenceDelta:
    """Risk evidence differences between previous and re-analyzed outputs."""

    added: tuple[RiskEvidence, ...]
    removed: tuple[RiskEvidence, ...]
    updated: tuple[tuple[RiskEvidence, RiskEvidence], ...]


@dataclass(frozen=True, slots=True)
class ReanalysisMetrics:
    """Runtime metrics for a selective re-analysis run."""

    modules_planned: int
    modules_executed: int
    duration_ms: float
    evidence_added_count: int
    evidence_removed_count: int
    evidence_updated_count: int


@dataclass(frozen=True, slots=True)
class ReanalysisResult:
    """Output of selective re-analysis driven by change detection."""

    watch_id: str
    execution_plan: ExecutionPlan
    executed_modules: tuple[ReanalysisModule, ...]
    new_evidence: tuple[RiskEvidence, ...]
    evidence_delta: EvidenceDelta
    metrics: ReanalysisMetrics
    change_result: ChangeDetectionResult
