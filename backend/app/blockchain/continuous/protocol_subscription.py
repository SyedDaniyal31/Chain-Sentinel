"""Protocol subscription helpers (M10.1)."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from app.blockchain.continuous.models import (
    WatchConfiguration,
    WatchStatus,
    WatchSubscription,
    WatchedProtocol,
)


def watch_id(chain_id: int, root_address: str) -> str:
    """Build a deterministic watch identifier for deduplication."""
    normalized = root_address.lower()
    return f"{chain_id}:{normalized}"


def build_watched_protocol(
    *,
    chain_id: int,
    root_address: str,
    protocol_name: str,
    registered_at: datetime | None = None,
    metadata: dict | None = None,
) -> WatchedProtocol:
    """Create a watched protocol record."""
    return WatchedProtocol(
        watch_id=watch_id(chain_id, root_address),
        chain_id=chain_id,
        root_address=root_address.lower(),
        protocol_name=protocol_name,
        registered_at=registered_at or _utc_now(),
        metadata=dict(metadata or {}),
    )


def build_subscription(
    *,
    protocol: WatchedProtocol,
    configuration: WatchConfiguration,
    status: WatchStatus = WatchStatus.ENABLED,
    baseline_scan: dict | None = None,
    last_execution_at: datetime | None = None,
    next_execution_at: datetime | None = None,
    created_at: datetime | None = None,
    updated_at: datetime | None = None,
) -> WatchSubscription:
    """Create a watch subscription from protocol identity and configuration."""
    timestamp = created_at or _utc_now()
    return WatchSubscription(
        subscription_id=protocol.watch_id,
        protocol=protocol,
        configuration=configuration,
        status=status,
        baseline_scan=baseline_scan,
        last_execution_at=last_execution_at,
        next_execution_at=next_execution_at,
        created_at=timestamp,
        updated_at=updated_at or timestamp,
    )


def merge_configuration(
    current: WatchConfiguration,
    updated: WatchConfiguration,
) -> WatchConfiguration:
    """Merge configuration updates while preserving unspecified cron metadata."""
    return WatchConfiguration(
        schedule_type=updated.schedule_type,
        cron_expression=updated.cron_expression if updated.cron_expression is not None else current.cron_expression,
        timezone=updated.timezone or current.timezone,
        metadata={**current.metadata, **updated.metadata},
    )


def event_id(watch_id_value: str, event_type: str, timestamp: datetime) -> str:
    """Build a deterministic watch event identifier."""
    payload = f"{watch_id_value}|{event_type}|{timestamp.isoformat()}"
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
    return f"{watch_id_value}:{event_type}:{digest}"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)
