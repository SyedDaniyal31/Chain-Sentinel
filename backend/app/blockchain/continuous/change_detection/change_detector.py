"""Change detection orchestrator (M10.2)."""

from __future__ import annotations

from datetime import datetime, timezone

from app.blockchain.continuous.change_detection.change_classifier import ChangeClassifier
from app.blockchain.continuous.change_detection.diff_engine import DiffEngine, RawChange, change_event_id
from app.blockchain.continuous.change_detection.models import ChangeDetectionResult, ChangeEvent, ProtocolSnapshot
from app.blockchain.continuous.change_detection.snapshot import ensure_protocol_compatibility
from app.blockchain.continuous.change_detection.snapshot_store import SnapshotStore


class ChangeDetector:
    """Compare baseline and current snapshots and emit structured change events."""

    def __init__(
        self,
        diff_engine: DiffEngine | None = None,
        classifier: ChangeClassifier | None = None,
        snapshot_store: SnapshotStore | None = None,
    ) -> None:
        self._diff_engine = diff_engine or DiffEngine()
        self._classifier = classifier or ChangeClassifier()
        self._snapshot_store = snapshot_store

    def detect(
        self,
        baseline: ProtocolSnapshot,
        current: ProtocolSnapshot,
        *,
        detected_at: datetime | None = None,
    ) -> ChangeDetectionResult:
        ensure_protocol_compatibility(baseline, current)
        timestamp = detected_at or _utc_now()
        raw_changes = self._diff_engine.diff(baseline, current)
        events = self._build_events(
            watch_id=baseline.watch_id,
            raw_changes=raw_changes,
            timestamp=timestamp,
        )
        return ChangeDetectionResult(
            watch_id=baseline.watch_id,
            baseline_snapshot_id=baseline.snapshot_id,
            current_snapshot_id=current.snapshot_id,
            detected_at=timestamp,
            changes=events,
            unchanged=len(events) == 0,
        )

    def detect_from_store(
        self,
        watch_id: str,
        current: ProtocolSnapshot,
        *,
        detected_at: datetime | None = None,
    ) -> ChangeDetectionResult:
        if self._snapshot_store is None:
            raise ValueError("snapshot store is required for detect_from_store")
        baseline = self._snapshot_store.get_baseline(watch_id)
        if baseline is None:
            raise ValueError(f"baseline snapshot not found for watch: {watch_id}")
        return self.detect(baseline, current, detected_at=detected_at)

    def _build_events(
        self,
        *,
        watch_id: str,
        raw_changes: tuple[RawChange, ...],
        timestamp: datetime,
    ) -> tuple[ChangeEvent, ...]:
        events: list[ChangeEvent] = []
        seen: set[str] = set()
        for change in raw_changes:
            event_id = change_event_id(
                watch_id=watch_id,
                change_type=change.change_type,
                before=change.before,
                after=change.after,
                affected_contracts=change.affected_contracts,
            )
            if event_id in seen:
                continue
            seen.add(event_id)
            severity, confidence = self._classifier.classify(change)
            events.append(
                ChangeEvent(
                    event_id=event_id,
                    change_type=change.change_type,
                    severity=severity,
                    before=change.before,
                    after=change.after,
                    affected_contracts=change.affected_contracts,
                    timestamp=timestamp,
                    confidence=confidence,
                    metadata={"watch_id": watch_id},
                )
            )
        return tuple(sorted(events, key=_event_sort_key))


def _event_sort_key(event: ChangeEvent) -> tuple[str, str, str]:
    return (
        event.change_type.value,
        ",".join(event.affected_contracts),
        event.event_id,
    )


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)
