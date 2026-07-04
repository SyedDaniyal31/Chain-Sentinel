"""Historical trend analysis (M10.6)."""

from __future__ import annotations

from decimal import Decimal

from app.blockchain.continuous.history.models import (
    AlertFrequencyMetrics,
    ChangeRecurrenceMetrics,
    HistoricalRecord,
    HistoryRecordType,
    RiskTrendMetrics,
    StabilityMetrics,
    TrendAnalysis,
)
from app.blockchain.continuous.risk_delta.models import RiskTrend

GOVERNANCE_CHANGE_TYPES = frozenset({"governance_changed", "owner_changed", "proxy_admin_changed"})
IMPLEMENTATION_CHANGE_TYPES = frozenset({"implementation_changed", "bytecode_changed"})
OWNERSHIP_CHANGE_TYPES = frozenset({"owner_changed", "proxy_admin_changed"})
TREASURY_CHANGE_TYPES = frozenset({"treasury_changed"})


class TrendAnalyzer:
    """Compute trend metrics from historical records."""

    def analyze(self, watch_id: str, records: tuple[HistoricalRecord, ...]) -> TrendAnalysis:
        risk_records = [item for item in records if item.record_type == HistoryRecordType.RISK_DELTA]
        alert_records = [item for item in records if item.record_type == HistoryRecordType.ALERT_BATCH]
        change_records = [item for item in records if item.record_type == HistoryRecordType.CHANGE_DETECTION]
        acknowledgement_records = [
            item for item in records if item.record_type == HistoryRecordType.ACKNOWLEDGEMENT
        ]

        return TrendAnalysis(
            watch_id=watch_id,
            risk_trend=_risk_trend_metrics(risk_records),
            alert_frequency=_alert_frequency_metrics(alert_records, acknowledgement_records, len(change_records)),
            change_recurrence=_change_recurrence_metrics(change_records),
            stability=_stability_metrics(change_records),
        )


def _risk_trend_metrics(records: list[HistoricalRecord]) -> RiskTrendMetrics:
    if not records:
        return RiskTrendMetrics(
            direction=RiskTrend.UNCHANGED,
            score_delta_total=Decimal("0.00"),
            delta_count=0,
            increasing_cycles=0,
            decreasing_cycles=0,
            unchanged_cycles=0,
        )

    score_total = Decimal("0.00")
    increasing = 0
    decreasing = 0
    unchanged = 0
    for record in records:
        trend = record.payload.get("trend", RiskTrend.UNCHANGED.value)
        score_total += Decimal(record.payload.get("score_delta", "0.00"))
        if trend == RiskTrend.INCREASED.value:
            increasing += 1
        elif trend == RiskTrend.DECREASED.value:
            decreasing += 1
        else:
            unchanged += 1

    if increasing > decreasing:
        direction = RiskTrend.INCREASED
    elif decreasing > increasing:
        direction = RiskTrend.DECREASED
    else:
        direction = RiskTrend.UNCHANGED

    return RiskTrendMetrics(
        direction=direction,
        score_delta_total=score_total,
        delta_count=len(records),
        increasing_cycles=increasing,
        decreasing_cycles=decreasing,
        unchanged_cycles=unchanged,
    )


def _alert_frequency_metrics(
    alert_records: list[HistoricalRecord],
    acknowledgement_records: list[HistoricalRecord],
    cycle_count: int,
) -> AlertFrequencyMetrics:
    total = 0
    critical = 0
    high = 0
    suppressed = 0
    for record in alert_records:
        total += int(record.payload.get("generated_count", 0))
        suppressed += int(record.payload.get("suppressed_count", 0))
        for severity in record.payload.get("severities", []):
            if severity == "critical":
                critical += 1
            elif severity == "high":
                high += 1

    cycles = max(cycle_count, 1)
    return AlertFrequencyMetrics(
        total_alerts=total,
        critical_alerts=critical,
        high_alerts=high,
        suppressed_alerts=suppressed,
        acknowledged_alerts=len(acknowledgement_records),
        alerts_per_cycle=Decimal(total) / Decimal(cycles),
    )


def _change_recurrence_metrics(records: list[HistoricalRecord]) -> ChangeRecurrenceMetrics:
    governance = 0
    implementation = 0
    ownership = 0
    treasury = 0
    for record in records:
        for change_type in record.payload.get("change_types", []):
            if change_type in GOVERNANCE_CHANGE_TYPES:
                governance += 1
            if change_type in IMPLEMENTATION_CHANGE_TYPES:
                implementation += 1
            if change_type in OWNERSHIP_CHANGE_TYPES:
                ownership += 1
            if change_type in TREASURY_CHANGE_TYPES:
                treasury += 1
    return ChangeRecurrenceMetrics(
        governance_changes=governance,
        implementation_changes=implementation,
        ownership_changes=ownership,
        treasury_changes=treasury,
    )


def _stability_metrics(records: list[HistoricalRecord]) -> StabilityMetrics:
    if not records:
        return StabilityMetrics(
            total_cycles=0,
            unchanged_cycles=0,
            stability_ratio=Decimal("1.00"),
            change_free_streak=0,
        )

    unchanged_cycles = sum(1 for item in records if item.payload.get("unchanged", False))
    total = len(records)
    ratio = Decimal(unchanged_cycles) / Decimal(total)
    streak = 0
    for record in reversed(records):
        if record.payload.get("unchanged", False):
            streak += 1
        else:
            break

    return StabilityMetrics(
        total_cycles=total,
        unchanged_cycles=unchanged_cycles,
        stability_ratio=ratio.quantize(Decimal("0.01")),
        change_free_streak=streak,
    )
