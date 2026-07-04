"""Historical retention and archival (M10.6)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.blockchain.continuous.history.baseline_store import BaselineStore
from app.blockchain.continuous.history.history_store import HistoryStore
from app.blockchain.continuous.history.models import ArchiveManifest, HistoricalRecord, RetentionPolicy


class RetentionEngine:
    """Apply configurable retention policies to historical records."""

    def __init__(
        self,
        *,
        history_store: HistoryStore,
        baseline_store: BaselineStore | None = None,
    ) -> None:
        self._history = history_store
        self._baseline = baseline_store

    def apply(
        self,
        watch_id: str,
        *,
        policy: RetentionPolicy | None = None,
        now: datetime | None = None,
    ) -> ArchiveManifest:
        timestamp = now or datetime.now(timezone.utc)
        active_policy = policy or RetentionPolicy()
        records = self._history.list_records(watch_id)
        protected_reference_ids = self._protected_reference_ids(watch_id, active_policy)

        remove_ids: set[str] = set()
        for record in records:
            if record.reference_id in protected_reference_ids:
                continue
            if self._is_expired(record, policy=active_policy, now=timestamp):
                remove_ids.add(record.record_id)

        remaining = [item for item in records if item.record_id not in remove_ids]
        if len(remaining) > active_policy.max_records_per_watch:
            removable = [
                item
                for item in sorted(remaining, key=_record_sort_key)
                if item.reference_id not in protected_reference_ids
            ]
            overflow = len(remaining) - active_policy.max_records_per_watch
            for record in removable[:overflow]:
                remove_ids.add(record.record_id)

        ordered_remove_ids = tuple(sorted(remove_ids))
        archived_ids = ordered_remove_ids if active_policy.archive_removed else ()
        self._history.remove_records(ordered_remove_ids)
        retained = len(self._history.list_records(watch_id))

        return ArchiveManifest(
            watch_id=watch_id,
            removed_record_ids=ordered_remove_ids,
            archived_record_ids=archived_ids,
            retained_count=retained,
            applied_at=timestamp,
        )

    def _protected_reference_ids(self, watch_id: str, policy: RetentionPolicy) -> set[str]:
        if not policy.retain_baseline or self._baseline is None:
            return set()
        baseline = self._baseline.get_baseline(watch_id)
        if baseline is None:
            return set()
        return {baseline.snapshot_id}

    def _is_expired(
        self,
        record: HistoricalRecord,
        *,
        policy: RetentionPolicy,
        now: datetime,
    ) -> bool:
        if policy.max_age_days <= 0:
            return False
        cutoff = now - timedelta(days=policy.max_age_days)
        return record.timestamp < cutoff


def _record_sort_key(record: HistoricalRecord) -> tuple[str, str]:
    return (record.timestamp.isoformat(), record.record_id)
