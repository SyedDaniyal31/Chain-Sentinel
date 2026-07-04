"""Snapshot archival helpers (M10.6)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.blockchain.continuous.change_detection.models import ProtocolSnapshot
from app.blockchain.continuous.history.baseline_store import BaselineStore
from app.blockchain.continuous.history.history_store import HistoryIngestor, HistoryStore
from app.blockchain.continuous.history.models import HistoricalRecord


@dataclass(frozen=True, slots=True)
class SnapshotArchiveResult:
    """Result of archiving a protocol snapshot."""

    snapshot: ProtocolSnapshot
    baseline_created: bool
    history_record: HistoricalRecord


class SnapshotArchiver:
    """Archive protocol snapshots into baseline and history stores."""

    def __init__(
        self,
        *,
        baseline_store: BaselineStore,
        history_store: HistoryStore,
        ingestor: HistoryIngestor | None = None,
    ) -> None:
        self._baseline = baseline_store
        self._history = history_store
        self._ingestor = ingestor or HistoryIngestor()

    def archive(
        self,
        snapshot: ProtocolSnapshot,
        *,
        as_baseline: bool = False,
    ) -> SnapshotArchiveResult:
        baseline_created = False
        if as_baseline or not self._baseline.has_baseline(snapshot.watch_id):
            baseline_created = self._baseline.set_baseline(snapshot)

        record = self._ingestor.ingest_snapshot(snapshot)
        self._history.append(record)
        return SnapshotArchiveResult(
            snapshot=snapshot,
            baseline_created=baseline_created,
            history_record=record,
        )

    def archive_cycle(
        self,
        snapshot: ProtocolSnapshot,
        *,
        archived_at: datetime | None = None,
    ) -> HistoricalRecord:
        record = self._ingestor.ingest_snapshot(snapshot)
        if archived_at is not None:
            record = HistoricalRecord(
                record_id=record.record_id,
                watch_id=record.watch_id,
                record_type=record.record_type,
                timestamp=archived_at,
                reference_id=record.reference_id,
                payload={**record.payload, "archived_at": archived_at.isoformat()},
            )
        self._history.append(record)
        return record
