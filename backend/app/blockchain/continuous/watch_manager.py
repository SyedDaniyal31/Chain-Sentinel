"""Watch lifecycle manager (M10.1)."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone

from app.blockchain.continuous.models import WatchEventType, WatchStatus, WatchSubscription
from app.blockchain.continuous.scheduler import WatchScheduler
from app.blockchain.continuous.watch_registry import WatchNotFoundError, WatchRegistry


class WatchManager:
    """Manage enable, disable, pause, resume, and delete operations for watches."""

    def __init__(
        self,
        registry: WatchRegistry | None = None,
        scheduler: WatchScheduler | None = None,
    ) -> None:
        self._registry = registry or WatchRegistry()
        self._scheduler = scheduler or WatchScheduler()

    def enable(self, watch_id_value: str, *, now: datetime | None = None) -> WatchSubscription:
        """Enable a disabled or paused watch."""
        return self._transition(
            watch_id_value,
            target_status=WatchStatus.ENABLED,
            event_type=WatchEventType.ENABLED,
            now=now,
            reschedule=True,
        )

    def disable(self, watch_id_value: str, *, now: datetime | None = None) -> WatchSubscription:
        """Disable a watch and clear scheduled execution."""
        return self._transition(
            watch_id_value,
            target_status=WatchStatus.DISABLED,
            event_type=WatchEventType.DISABLED,
            now=now,
            clear_schedule=True,
        )

    def pause(self, watch_id_value: str, *, now: datetime | None = None) -> WatchSubscription:
        """Pause a watch and retain baseline state."""
        return self._transition(
            watch_id_value,
            target_status=WatchStatus.PAUSED,
            event_type=WatchEventType.PAUSED,
            now=now,
            clear_schedule=True,
        )

    def resume(self, watch_id_value: str, *, now: datetime | None = None) -> WatchSubscription:
        """Resume a paused watch and recompute next execution."""
        subscription = self._require_watch(watch_id_value)
        if subscription.status != WatchStatus.PAUSED:
            raise ValueError(f"watch is not paused: {watch_id_value}")
        return self._transition(
            watch_id_value,
            target_status=WatchStatus.ENABLED,
            event_type=WatchEventType.RESUMED,
            now=now,
            reschedule=True,
        )

    def delete(self, watch_id_value: str) -> bool:
        """Delete a watch from the registry."""
        if self._registry.get_watch(watch_id_value) is None:
            raise WatchNotFoundError(f"watch not found: {watch_id_value}")
        return self._registry.delete_watch(watch_id_value)

    def _transition(
        self,
        watch_id_value: str,
        *,
        target_status: WatchStatus,
        event_type: WatchEventType,
        now: datetime | None,
        reschedule: bool = False,
        clear_schedule: bool = False,
    ) -> WatchSubscription:
        subscription = self._require_watch(watch_id_value)
        timestamp = now or _utc_now()
        next_execution = subscription.next_execution_at
        if clear_schedule:
            next_execution = None
        elif reschedule:
            next_execution = self._scheduler.schedule_initial(
                replace(subscription, status=WatchStatus.ENABLED),
                now=timestamp,
            )
        updated = replace(
            subscription,
            status=target_status,
            next_execution_at=next_execution,
            updated_at=timestamp,
        )
        self._registry.save_subscription(updated)
        self._registry.emit_event(
            watch_id=watch_id_value,
            event_type=event_type,
            timestamp=timestamp,
        )
        return updated

    def _require_watch(self, watch_id_value: str) -> WatchSubscription:
        subscription = self._registry.get_watch(watch_id_value)
        if subscription is None:
            raise WatchNotFoundError(f"watch not found: {watch_id_value}")
        return subscription


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)
