"""Baseline history and timeline domain models (M10.6)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any

from app.blockchain.continuous.risk_delta.models import RiskTrend


class HistoryRecordType(StrEnum):
    """Categories of immutable historical records."""

    SNAPSHOT = "snapshot"
    CHANGE_DETECTION = "change_detection"
    REANALYSIS = "reanalysis"
    EVIDENCE_DELTA = "evidence_delta"
    RISK_DELTA = "risk_delta"
    ALERT_BATCH = "alert_batch"
    ACKNOWLEDGEMENT = "acknowledgement"


class TimelineEntryKind(StrEnum):
    """Timeline event categories for dashboards and analysis."""

    SNAPSHOT = "snapshot"
    CHANGE = "change"
    EVIDENCE_DELTA = "evidence_delta"
    RISK_DELTA = "risk_delta"
    ALERT = "alert"
    ACKNOWLEDGEMENT = "acknowledgement"


@dataclass(frozen=True, slots=True)
class HistoricalRecord:
    """Immutable envelope for a persisted monitoring artifact."""

    record_id: str
    watch_id: str
    record_type: HistoryRecordType
    timestamp: datetime
    reference_id: str
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class TimelineEntry:
    """Single chronological timeline event."""

    entry_id: str
    watch_id: str
    kind: TimelineEntryKind
    timestamp: datetime
    title: str
    summary: str
    reference_id: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class RiskTrendMetrics:
    """Risk posture trend derived from historical deltas."""

    direction: RiskTrend
    score_delta_total: Decimal
    delta_count: int
    increasing_cycles: int
    decreasing_cycles: int
    unchanged_cycles: int


@dataclass(frozen=True, slots=True)
class AlertFrequencyMetrics:
    """Alert volume metrics over the observed history."""

    total_alerts: int
    critical_alerts: int
    high_alerts: int
    suppressed_alerts: int
    acknowledged_alerts: int
    alerts_per_cycle: Decimal


@dataclass(frozen=True, slots=True)
class ChangeRecurrenceMetrics:
    """Repeated change detection metrics."""

    governance_changes: int
    implementation_changes: int
    ownership_changes: int
    treasury_changes: int


@dataclass(frozen=True, slots=True)
class StabilityMetrics:
    """Protocol stability indicators."""

    total_cycles: int
    unchanged_cycles: int
    stability_ratio: Decimal
    change_free_streak: int


@dataclass(frozen=True, slots=True)
class TrendAnalysis:
    """Aggregate trend analysis for a watch history window."""

    watch_id: str
    risk_trend: RiskTrendMetrics
    alert_frequency: AlertFrequencyMetrics
    change_recurrence: ChangeRecurrenceMetrics
    stability: StabilityMetrics


@dataclass(frozen=True, slots=True)
class RetentionPolicy:
    """Configurable retention and archival policy."""

    max_records_per_watch: int = 1000
    max_age_days: int = 365
    retain_baseline: bool = True
    archive_removed: bool = True


@dataclass(frozen=True, slots=True)
class ArchiveManifest:
    """Summary of records removed or archived by retention."""

    watch_id: str
    removed_record_ids: tuple[str, ...]
    archived_record_ids: tuple[str, ...]
    retained_count: int
    applied_at: datetime


@dataclass(frozen=True, slots=True)
class TimelineReport:
    """Immutable timeline output for dashboards and AI analysis."""

    watch_id: str
    generated_at: datetime
    entries: tuple[TimelineEntry, ...]
    trends: TrendAnalysis
    record_count: int
