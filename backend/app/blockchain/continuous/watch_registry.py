"""Watch registry for continuous protocol monitoring (M10.1)."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone

from app.blockchain.continuous.models import (
    WatchConfiguration,
    WatchEvent,
    WatchEventType,
    WatchStatus,
    WatchSubscription,
)
from app.blockchain.continuous.persistence import WatchPersistenceStore
from app.blockchain.continuous.protocol_subscription import (
    build_subscription,
    build_watched_protocol,
    event_id,
    merge_configuration,
    watch_id,
)
from app.blockchain.continuous.scheduler import WatchScheduler


class DuplicateWatchError(ValueError):
    """Raised when registering a protocol that is already watched."""


class WatchNotFoundError(ValueError):
    """Raised when a watch identifier does not exist."""


class WatchRegistry:
    """Register, configure, and list watched protocols."""

    def __init__(
        self,
        persistence: WatchPersistenceStore | None = None,
        scheduler: WatchScheduler | None = None,
    ) -> None:
        self._persistence = persistence or _default_persistence()
        self._scheduler = scheduler or WatchScheduler()

    def register(
        self,
        *,
        chain_id: int,
        root_address: str,
        protocol_name: str,
        configuration: WatchConfiguration | None = None,
        baseline_scan: dict | None = None,
        metadata: dict | None = None,
        now: datetime | None = None,
    ) -> WatchSubscription:
        """Register a protocol for continuous monitoring."""
        identifier = watch_id(chain_id, root_address)
        if self._persistence.get_subscription(identifier) is not None:
            raise DuplicateWatchError(f"watch already registered: {identifier}")

        timestamp = now or _utc_now()
        protocol = build_watched_protocol(
            chain_id=chain_id,
            root_address=root_address,
            protocol_name=protocol_name,
            registered_at=timestamp,
            metadata=metadata,
        )
        config = configuration or WatchConfiguration()
        subscription = build_subscription(
            protocol=protocol,
            configuration=config,
            status=WatchStatus.ENABLED,
            baseline_scan=baseline_scan,
            created_at=timestamp,
            updated_at=timestamp,
        )
        subscription = replace(
            subscription,
            next_execution_at=self._scheduler.schedule_initial(subscription, now=timestamp),
        )
        self._persistence.save_subscription(subscription)
        self._record_event(
            watch_id=identifier,
            event_type=WatchEventType.REGISTERED,
            timestamp=timestamp,
            metadata={"protocol_name": protocol_name},
        )
        if subscription.next_execution_at is not None:
            self._record_event(
                watch_id=identifier,
                event_type=WatchEventType.SCHEDULED,
                timestamp=timestamp,
                metadata={"next_execution_at": subscription.next_execution_at.isoformat()},
            )
        return subscription

    def unregister(self, watch_id_value: str) -> bool:
        """Remove a watch subscription from the registry."""
        subscription = self._require_subscription(watch_id_value)
        deleted = self._persistence.delete_subscription(watch_id_value)
        if deleted:
            self._record_event(
                watch_id=watch_id_value,
                event_type=WatchEventType.UNREGISTERED,
                timestamp=_utc_now(),
                metadata={"protocol_name": subscription.protocol.protocol_name},
            )
        return deleted

    def update_configuration(
        self,
        watch_id_value: str,
        configuration: WatchConfiguration,
        *,
        now: datetime | None = None,
    ) -> WatchSubscription:
        """Update watch configuration and recompute scheduling."""
        subscription = self._require_subscription(watch_id_value)
        timestamp = now or _utc_now()
        merged = merge_configuration(subscription.configuration, configuration)
        updated = replace(
            subscription,
            configuration=merged,
            updated_at=timestamp,
            next_execution_at=self._scheduler.schedule_initial(
                replace(subscription, configuration=merged),
                now=timestamp,
            )
            if subscription.status == WatchStatus.ENABLED
            else None,
        )
        self._persistence.save_subscription(updated)
        self._record_event(
            watch_id=watch_id_value,
            event_type=WatchEventType.CONFIG_UPDATED,
            timestamp=timestamp,
            metadata={"schedule_type": merged.schedule_type.value},
        )
        return updated

    def list_watches(self) -> tuple[WatchSubscription, ...]:
        """Return all registered watches in deterministic order."""
        return self._persistence.list_subscriptions()

    def get_watch(self, watch_id_value: str) -> WatchSubscription | None:
        """Return a single watch subscription."""
        return self._persistence.get_subscription(watch_id_value)

    def record_execution(
        self,
        watch_id_value: str,
        *,
        executed_at: datetime | None = None,
        scan_snapshot: dict | None = None,
    ) -> WatchSubscription:
        """Persist execution timestamps and optional scan snapshot."""
        subscription = self._require_subscription(watch_id_value)
        timestamp = executed_at or _utc_now()
        baseline = subscription.baseline_scan or scan_snapshot
        updated = replace(
            subscription,
            baseline_scan=baseline,
            last_execution_at=timestamp,
            next_execution_at=self._scheduler.after_execution(subscription, executed_at=timestamp)
            if subscription.status == WatchStatus.ENABLED
            else subscription.next_execution_at,
            updated_at=timestamp,
        )
        self._persistence.save_subscription(updated)
        self._record_event(
            watch_id=watch_id_value,
            event_type=WatchEventType.EXECUTED,
            timestamp=timestamp,
            metadata={"scan_snapshot": scan_snapshot or {}},
        )
        return updated

    def delete_watch(self, watch_id_value: str) -> bool:
        """Remove a watch and emit a deleted lifecycle event."""
        subscription = self._require_subscription(watch_id_value)
        deleted = self._persistence.delete_subscription(watch_id_value)
        if deleted:
            self._record_event(
                watch_id=watch_id_value,
                event_type=WatchEventType.DELETED,
                timestamp=_utc_now(),
                metadata={"protocol_name": subscription.protocol.protocol_name},
            )
        return deleted

    def save_subscription(self, subscription: WatchSubscription) -> None:
        """Persist an updated watch subscription."""
        self._persistence.save_subscription(subscription)

    def emit_event(
        self,
        *,
        watch_id: str,
        event_type: WatchEventType,
        timestamp: datetime | None = None,
        metadata: dict | None = None,
    ) -> WatchEvent:
        """Record a watch lifecycle audit event."""
        moment = timestamp or _utc_now()
        return self._record_event(
            watch_id=watch_id,
            event_type=event_type,
            timestamp=moment,
            metadata=metadata,
        )

    def list_events(self, watch_id_value: str | None = None) -> tuple[WatchEvent, ...]:
        """Return lifecycle audit events."""
        return self._persistence.list_events(watch_id_value)

    def _require_subscription(self, watch_id_value: str) -> WatchSubscription:
        subscription = self._persistence.get_subscription(watch_id_value)
        if subscription is None:
            raise WatchNotFoundError(f"watch not found: {watch_id_value}")
        return subscription

    def _record_event(
        self,
        *,
        watch_id: str,
        event_type: WatchEventType,
        timestamp: datetime,
        metadata: dict | None = None,
    ) -> WatchEvent:
        event = WatchEvent(
            event_id=event_id(watch_id, event_type.value, timestamp),
            event_type=event_type,
            watch_id=watch_id,
            timestamp=timestamp,
            metadata=dict(metadata or {}),
        )
        self._persistence.append_event(event)
        return event


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _default_persistence() -> WatchPersistenceStore:
    from app.blockchain.continuous.persistence import InMemoryWatchPersistence

    return InMemoryWatchPersistence()
