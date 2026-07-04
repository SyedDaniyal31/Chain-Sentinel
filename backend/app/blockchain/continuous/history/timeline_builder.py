"""Chronological timeline generation (M10.6)."""

from __future__ import annotations

from datetime import datetime, timezone

from app.blockchain.continuous.history.history_store import HistoryStore
from app.blockchain.continuous.history.models import (
    HistoricalRecord,
    HistoryRecordType,
    TimelineEntry,
    TimelineEntryKind,
    TimelineReport,
)
from app.blockchain.continuous.history.trend_analyzer import TrendAnalyzer


class TimelineBuilder:
    """Build immutable timeline reports from historical records."""

    def __init__(
        self,
        *,
        history_store: HistoryStore,
        trend_analyzer: TrendAnalyzer | None = None,
    ) -> None:
        self._history = history_store
        self._trends = trend_analyzer or TrendAnalyzer()

    def build(
        self,
        watch_id: str,
        *,
        generated_at: datetime | None = None,
    ) -> TimelineReport:
        timestamp = generated_at or datetime.now(timezone.utc)
        records = self._history.list_records(watch_id)
        entries = tuple(self._entry_for_record(record) for record in records)
        entries = tuple(sorted(entries, key=_entry_sort_key))
        trends = self._trends.analyze(watch_id, records)
        return TimelineReport(
            watch_id=watch_id,
            generated_at=timestamp,
            entries=entries,
            trends=trends,
            record_count=len(records),
        )

    def _entry_for_record(self, record: HistoricalRecord) -> TimelineEntry:
        kind = _kind_for_record(record.record_type)
        title, summary = _title_and_summary(record)
        return TimelineEntry(
            entry_id=f"{record.record_id}:timeline",
            watch_id=record.watch_id,
            kind=kind,
            timestamp=record.timestamp,
            title=title,
            summary=summary,
            reference_id=record.reference_id,
            metadata={
                "record_id": record.record_id,
                "record_type": record.record_type.value,
            },
        )


def _kind_for_record(record_type: HistoryRecordType) -> TimelineEntryKind:
    mapping = {
        HistoryRecordType.SNAPSHOT: TimelineEntryKind.SNAPSHOT,
        HistoryRecordType.CHANGE_DETECTION: TimelineEntryKind.CHANGE,
        HistoryRecordType.REANALYSIS: TimelineEntryKind.EVIDENCE_DELTA,
        HistoryRecordType.EVIDENCE_DELTA: TimelineEntryKind.EVIDENCE_DELTA,
        HistoryRecordType.RISK_DELTA: TimelineEntryKind.RISK_DELTA,
        HistoryRecordType.ALERT_BATCH: TimelineEntryKind.ALERT,
        HistoryRecordType.ACKNOWLEDGEMENT: TimelineEntryKind.ACKNOWLEDGEMENT,
    }
    return mapping[record_type]


def _title_and_summary(record: HistoricalRecord) -> tuple[str, str]:
    payload = record.payload
    if record.record_type == HistoryRecordType.SNAPSHOT:
        return ("Protocol snapshot captured", f"Snapshot {record.reference_id}")
    if record.record_type == HistoryRecordType.CHANGE_DETECTION:
        count = payload.get("change_count", 0)
        unchanged = payload.get("unchanged", False)
        if unchanged:
            return ("No protocol changes detected", "Baseline comparison unchanged")
        return (f"{count} protocol change(s) detected", ", ".join(payload.get("change_types", [])))
    if record.record_type == HistoryRecordType.REANALYSIS:
        modules = ", ".join(payload.get("modules_executed", []))
        return ("Selective re-analysis completed", f"Modules executed: {modules or 'none'}")
    if record.record_type == HistoryRecordType.EVIDENCE_DELTA:
        return (
            "Evidence delta recorded",
            (
                f"added={payload.get('added_count', 0)}, "
                f"removed={payload.get('removed_count', 0)}, "
                f"updated={payload.get('updated_count', 0)}"
            ),
        )
    if record.record_type == HistoryRecordType.RISK_DELTA:
        return (
            f"Risk posture {payload.get('trend', 'unchanged')}",
            payload.get("headline", "Risk delta computed"),
        )
    if record.record_type == HistoryRecordType.ALERT_BATCH:
        return (
            f"{payload.get('generated_count', 0)} alert(s) generated",
            f"suppressed={payload.get('suppressed_count', 0)}",
        )
    if record.record_type == HistoryRecordType.ACKNOWLEDGEMENT:
        return (
            f"Alert acknowledged: {payload.get('title', record.reference_id)}",
            f"state={payload.get('acknowledgement_state', 'acknowledged')}",
        )
    return ("Historical record", record.reference_id)


def _entry_sort_key(entry: TimelineEntry) -> tuple[str, str, str]:
    return (entry.timestamp.isoformat(), entry.kind.value, entry.entry_id)
