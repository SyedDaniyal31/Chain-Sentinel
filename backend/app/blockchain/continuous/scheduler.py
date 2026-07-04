"""Watch scheduling utilities (M10.1)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.blockchain.continuous.models import WatchConfiguration, WatchScheduleType, WatchStatus, WatchSubscription


class WatchScheduler:
    """Compute next execution times for watch subscriptions."""

    INTERVALS: dict[WatchScheduleType, timedelta | None] = {
        WatchScheduleType.MANUAL: None,
        WatchScheduleType.HOURLY: timedelta(hours=1),
        WatchScheduleType.DAILY: timedelta(days=1),
        WatchScheduleType.WEEKLY: timedelta(weeks=1),
        WatchScheduleType.CRON: None,
    }

    def compute_next_execution(
        self,
        configuration: WatchConfiguration,
        *,
        reference_time: datetime,
    ) -> datetime | None:
        """Return the next scheduled execution time, or None for manual watches."""
        interval = self.INTERVALS.get(configuration.schedule_type)
        if interval is None:
            if configuration.schedule_type == WatchScheduleType.CRON:
                return self._compute_cron_next(configuration, reference_time=reference_time)
            return None
        normalized = _ensure_utc(reference_time)
        return normalized + interval

    def is_due(
        self,
        subscription: WatchSubscription,
        *,
        now: datetime,
    ) -> bool:
        """Return True when a scheduled watch is due for execution."""
        if subscription.status != WatchStatus.ENABLED:
            return False
        if subscription.configuration.schedule_type == WatchScheduleType.MANUAL:
            return False
        if subscription.next_execution_at is None:
            return False
        return _ensure_utc(now) >= _ensure_utc(subscription.next_execution_at)

    def schedule_initial(
        self,
        subscription: WatchSubscription,
        *,
        now: datetime,
    ) -> datetime | None:
        """Compute the first next_execution_at after registration or resume."""
        if subscription.configuration.schedule_type == WatchScheduleType.MANUAL:
            return None
        return self.compute_next_execution(subscription.configuration, reference_time=now)

    def after_execution(
        self,
        subscription: WatchSubscription,
        *,
        executed_at: datetime,
    ) -> datetime | None:
        """Compute next execution after a completed scan."""
        return self.compute_next_execution(
            subscription.configuration,
            reference_time=executed_at,
        )

    def _compute_cron_next(
        self,
        configuration: WatchConfiguration,
        *,
        reference_time: datetime,
    ) -> datetime | None:
        """Placeholder for future cron expression evaluation."""
        if not configuration.cron_expression:
            return None
        return None


def _ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
