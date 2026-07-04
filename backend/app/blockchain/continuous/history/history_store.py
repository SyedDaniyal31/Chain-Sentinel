"""Append-only historical record storage (M10.6)."""

from __future__ import annotations

import hashlib
import json
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from app.blockchain.continuous.alerting.models import AlertBatch, SecurityAlert
from app.blockchain.continuous.change_detection.models import ChangeDetectionResult, ProtocolSnapshot
from app.blockchain.continuous.change_detection.snapshot_store import serialize_snapshot
from app.blockchain.continuous.history.models import HistoricalRecord, HistoryRecordType
from app.blockchain.continuous.reanalysis.models import ReanalysisResult
from app.blockchain.continuous.risk_delta.models import RiskDeltaReport


class HistoryStore(ABC):
    """Abstract append-only store for monitoring history."""

    @abstractmethod
    def append(self, record: HistoricalRecord) -> None:
        """Persist an immutable historical record."""

    @abstractmethod
    def list_records(
        self,
        watch_id: str,
        *,
        record_type: HistoryRecordType | None = None,
    ) -> tuple[HistoricalRecord, ...]:
        """Return records for a watch in deterministic order."""

    @abstractmethod
    def get_record(self, record_id: str) -> HistoricalRecord | None:
        """Load a record by identifier."""

    @abstractmethod
    def remove_records(self, record_ids: tuple[str, ...]) -> int:
        """Remove records by identifier. Returns count removed."""


class InMemoryHistoryStore(HistoryStore):
    """In-memory append-only history store."""

    def __init__(self) -> None:
        self._records: dict[str, HistoricalRecord] = {}
        self._watch_index: dict[str, list[str]] = {}

    def append(self, record: HistoricalRecord) -> None:
        if record.record_id in self._records:
            return
        self._records[record.record_id] = record
        self._watch_index.setdefault(record.watch_id, []).append(record.record_id)

    def list_records(
        self,
        watch_id: str,
        *,
        record_type: HistoryRecordType | None = None,
    ) -> tuple[HistoricalRecord, ...]:
        record_ids = self._watch_index.get(watch_id, [])
        records = [self._records[item] for item in record_ids if item in self._records]
        if record_type is not None:
            records = [item for item in records if item.record_type == record_type]
        return tuple(sorted(records, key=_record_sort_key))

    def get_record(self, record_id: str) -> HistoricalRecord | None:
        return self._records.get(record_id)

    def remove_records(self, record_ids: tuple[str, ...]) -> int:
        removed = 0
        for record_id in record_ids:
            record = self._records.pop(record_id, None)
            if record is None:
                continue
            removed += 1
            watch_ids = self._watch_index.get(record.watch_id, [])
            if record_id in watch_ids:
                watch_ids.remove(record_id)
        return removed


class HistoryIngestor:
    """Archive pipeline artifacts into immutable historical records."""

    def ingest_snapshot(self, snapshot: ProtocolSnapshot) -> HistoricalRecord:
        record = build_record(
            watch_id=snapshot.watch_id,
            record_type=HistoryRecordType.SNAPSHOT,
            timestamp=snapshot.captured_at,
            reference_id=snapshot.snapshot_id,
            payload={
                "snapshot": serialize_snapshot(snapshot),
                "chain_id": snapshot.chain_id,
                "root_address": snapshot.root_address,
            },
        )
        return record

    def ingest_change_result(self, result: ChangeDetectionResult) -> HistoricalRecord:
        return build_record(
            watch_id=result.watch_id,
            record_type=HistoryRecordType.CHANGE_DETECTION,
            timestamp=result.detected_at,
            reference_id=f"{result.baseline_snapshot_id}:{result.current_snapshot_id}",
            payload={
                "baseline_snapshot_id": result.baseline_snapshot_id,
                "current_snapshot_id": result.current_snapshot_id,
                "unchanged": result.unchanged,
                "change_count": len(result.changes),
                "change_types": [item.change_type.value for item in result.changes],
            },
        )

    def ingest_reanalysis_result(self, result: ReanalysisResult) -> HistoricalRecord:
        return build_record(
            watch_id=result.watch_id,
            record_type=HistoryRecordType.REANALYSIS,
            timestamp=result.change_result.detected_at,
            reference_id=result.execution_plan.plan_id,
            payload={
                "plan_id": result.execution_plan.plan_id,
                "modules_executed": [item.value for item in result.executed_modules],
                "evidence_added_count": result.metrics.evidence_added_count,
                "evidence_removed_count": result.metrics.evidence_removed_count,
                "evidence_updated_count": result.metrics.evidence_updated_count,
            },
        )

    def ingest_evidence_delta(self, result: ReanalysisResult) -> HistoricalRecord:
        delta = result.evidence_delta
        return build_record(
            watch_id=result.watch_id,
            record_type=HistoryRecordType.EVIDENCE_DELTA,
            timestamp=result.change_result.detected_at,
            reference_id=f"{result.execution_plan.plan_id}:evidence",
            payload={
                "added_count": len(delta.added),
                "removed_count": len(delta.removed),
                "updated_count": len(delta.updated),
                "added_signals": sorted(
                    {
                        item.metadata.get("signal", item.reason)
                        for item in delta.added
                    }
                ),
            },
        )

    def ingest_risk_delta(self, report: RiskDeltaReport, *, captured_at: datetime) -> HistoricalRecord:
        return build_record(
            watch_id=report.watch_id,
            record_type=HistoryRecordType.RISK_DELTA,
            timestamp=captured_at,
            reference_id=f"{report.watch_id}:risk:{captured_at.isoformat()}",
            payload={
                "trend": report.trend.value,
                "score_delta": str(report.delta.score_delta),
                "previous_score": str(report.previous_summary.total_score),
                "current_score": str(report.current_summary.total_score),
                "headline": report.explanation.headline,
                "added_count": report.evidence_summary.added_count,
                "removed_count": report.evidence_summary.removed_count,
                "updated_count": report.evidence_summary.updated_count,
            },
        )

    def ingest_alert_batch(self, batch: AlertBatch) -> tuple[HistoricalRecord, ...]:
        records: list[HistoricalRecord] = []
        records.append(
            build_record(
                watch_id=batch.watch_id,
                record_type=HistoryRecordType.ALERT_BATCH,
                timestamp=batch.generated_at,
                reference_id=f"{batch.watch_id}:alerts:{batch.generated_at.isoformat()}",
                payload={
                    "generated_count": len(batch.generated_alerts),
                    "suppressed_count": len(batch.suppressed_alerts),
                    "alert_ids": [item.alert_id for item in batch.generated_alerts],
                    "severities": [item.severity.value for item in batch.generated_alerts],
                    "rule_types": [item.rule_type.value for item in batch.generated_alerts],
                },
            )
        )
        for alert in batch.generated_alerts:
            if alert.acknowledgement_state.value != "pending":
                records.append(self.ingest_acknowledgement(alert))
        return tuple(records)

    def ingest_acknowledgement(self, alert: SecurityAlert) -> HistoricalRecord:
        watch_id = alert.metadata.get("watch_id", alert.affected_protocol)
        return build_record(
            watch_id=watch_id,
            record_type=HistoryRecordType.ACKNOWLEDGEMENT,
            timestamp=alert.timestamp,
            reference_id=alert.alert_id,
            payload={
                "alert_id": alert.alert_id,
                "severity": alert.severity.value,
                "rule_type": alert.rule_type.value,
                "acknowledgement_state": alert.acknowledgement_state.value,
                "title": alert.title,
            },
        )


def build_record_id(
    *,
    watch_id: str,
    record_type: HistoryRecordType,
    reference_id: str,
    timestamp: datetime,
) -> str:
    fingerprint = "|".join([watch_id, record_type.value, reference_id, timestamp.isoformat()])
    digest = hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()[:16]
    return f"{watch_id}:history:{record_type.value}:{digest}"


def build_record(
    *,
    watch_id: str,
    record_type: HistoryRecordType,
    timestamp: datetime,
    reference_id: str,
    payload: dict[str, Any],
) -> HistoricalRecord:
    return HistoricalRecord(
        record_id=build_record_id(
            watch_id=watch_id,
            record_type=record_type,
            reference_id=reference_id,
            timestamp=timestamp,
        ),
        watch_id=watch_id,
        record_type=record_type,
        timestamp=timestamp,
        reference_id=reference_id,
        payload=payload,
    )


def serialize_record(record: HistoricalRecord) -> dict[str, Any]:
    return {
        "record_id": record.record_id,
        "watch_id": record.watch_id,
        "record_type": record.record_type.value,
        "timestamp": record.timestamp.isoformat(),
        "reference_id": record.reference_id,
        "payload": record.payload,
    }


def deserialize_record(payload: dict[str, Any]) -> HistoricalRecord:
    return HistoricalRecord(
        record_id=payload["record_id"],
        watch_id=payload["watch_id"],
        record_type=HistoryRecordType(payload["record_type"]),
        timestamp=datetime.fromisoformat(payload["timestamp"]),
        reference_id=payload["reference_id"],
        payload=dict(payload.get("payload", {})),
    )


def dump_history_store(store: InMemoryHistoryStore) -> str:
    payload = {
        "records": [
            serialize_record(store._records[key])
            for key in sorted(store._records.keys())
        ]
    }
    return json.dumps(payload, sort_keys=True)


def load_history_store(payload: str | dict[str, Any]) -> InMemoryHistoryStore:
    store = InMemoryHistoryStore()
    data = json.loads(payload) if isinstance(payload, str) else payload
    for item in data.get("records", []):
        store.append(deserialize_record(item))
    return store


def _record_sort_key(record: HistoricalRecord) -> tuple[str, str, str]:
    return (record.timestamp.isoformat(), record.record_type.value, record.record_id)
