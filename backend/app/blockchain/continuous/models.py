"""Continuous monitoring domain models (M10.1)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any


class WatchScheduleType(StrEnum):
    """Supported watch scan schedules."""

    MANUAL = "manual"
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    CRON = "cron"


class WatchStatus(StrEnum):
    """Lifecycle status for a watch subscription."""

    ENABLED = "enabled"
    DISABLED = "disabled"
    PAUSED = "paused"


class WatchEventType(StrEnum):
    """Audit events emitted during watch lifecycle changes."""

    REGISTERED = "registered"
    UNREGISTERED = "unregistered"
    CONFIG_UPDATED = "config_updated"
    ENABLED = "enabled"
    DISABLED = "disabled"
    PAUSED = "paused"
    RESUMED = "resumed"
    DELETED = "deleted"
    SCHEDULED = "scheduled"
    EXECUTED = "executed"


@dataclass(frozen=True, slots=True)
class WatchConfiguration:
    """Scheduling and scan configuration for a watched protocol."""

    schedule_type: WatchScheduleType = WatchScheduleType.MANUAL
    cron_expression: str | None = None
    timezone: str = "UTC"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class WatchedProtocol:
    """Registered protocol identity under continuous monitoring."""

    watch_id: str
    chain_id: int
    root_address: str
    protocol_name: str
    registered_at: datetime
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class WatchSubscription:
    """Full watch subscription including schedule and execution state."""

    subscription_id: str
    protocol: WatchedProtocol
    configuration: WatchConfiguration
    status: WatchStatus
    baseline_scan: dict[str, Any] | None
    last_execution_at: datetime | None
    next_execution_at: datetime | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class WatchEvent:
    """Immutable audit record for watch lifecycle transitions."""

    event_id: str
    event_type: WatchEventType
    watch_id: str
    timestamp: datetime
    metadata: dict[str, Any] = field(default_factory=dict)
