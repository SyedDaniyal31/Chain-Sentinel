"""Watch persistence layer (M10.1)."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import asdict
from datetime import datetime
from typing import Any

from app.blockchain.continuous.models import (
    WatchConfiguration,
    WatchEvent,
    WatchEventType,
    WatchScheduleType,
    WatchStatus,
    WatchSubscription,
    WatchedProtocol,
)


class WatchPersistenceStore(ABC):
    """Abstract persistence for watch subscriptions and audit events."""

    @abstractmethod
    def save_subscription(self, subscription: WatchSubscription) -> None:
        """Persist or update a watch subscription."""

    @abstractmethod
    def get_subscription(self, watch_id: str) -> WatchSubscription | None:
        """Load a watch subscription by identifier."""

    @abstractmethod
    def delete_subscription(self, watch_id: str) -> bool:
        """Remove a watch subscription."""

    @abstractmethod
    def list_subscriptions(self) -> tuple[WatchSubscription, ...]:
        """Return all persisted subscriptions in deterministic order."""

    @abstractmethod
    def append_event(self, event: WatchEvent) -> None:
        """Persist a watch lifecycle event."""

    @abstractmethod
    def list_events(self, watch_id: str | None = None) -> tuple[WatchEvent, ...]:
        """Return audit events, optionally filtered by watch identifier."""


class InMemoryWatchPersistence(WatchPersistenceStore):
    """In-memory watch persistence for tests and development."""

    def __init__(self) -> None:
        self._subscriptions: dict[str, WatchSubscription] = {}
        self._events: list[WatchEvent] = []

    def save_subscription(self, subscription: WatchSubscription) -> None:
        self._subscriptions[subscription.subscription_id] = subscription

    def get_subscription(self, watch_id: str) -> WatchSubscription | None:
        return self._subscriptions.get(watch_id)

    def delete_subscription(self, watch_id: str) -> bool:
        return self._subscriptions.pop(watch_id, None) is not None

    def list_subscriptions(self) -> tuple[WatchSubscription, ...]:
        return tuple(
            self._subscriptions[key]
            for key in sorted(self._subscriptions.keys())
        )

    def append_event(self, event: WatchEvent) -> None:
        self._events.append(event)

    def list_events(self, watch_id: str | None = None) -> tuple[WatchEvent, ...]:
        events = self._events
        if watch_id is not None:
            events = [item for item in events if item.watch_id == watch_id]
        return tuple(events)


def serialize_subscription(subscription: WatchSubscription) -> dict[str, Any]:
    """Convert a watch subscription to a JSON-serializable dictionary."""
    return {
        "subscription_id": subscription.subscription_id,
        "protocol": _serialize_protocol(subscription.protocol),
        "configuration": _serialize_configuration(subscription.configuration),
        "status": subscription.status.value,
        "baseline_scan": subscription.baseline_scan,
        "last_execution_at": _serialize_datetime(subscription.last_execution_at),
        "next_execution_at": _serialize_datetime(subscription.next_execution_at),
        "created_at": _serialize_datetime(subscription.created_at),
        "updated_at": _serialize_datetime(subscription.updated_at),
    }


def deserialize_subscription(payload: dict[str, Any]) -> WatchSubscription:
    """Restore a watch subscription from a serialized dictionary."""
    return WatchSubscription(
        subscription_id=str(payload["subscription_id"]),
        protocol=_deserialize_protocol(payload["protocol"]),
        configuration=_deserialize_configuration(payload["configuration"]),
        status=WatchStatus(str(payload["status"])),
        baseline_scan=payload.get("baseline_scan"),
        last_execution_at=_deserialize_datetime(payload.get("last_execution_at")),
        next_execution_at=_deserialize_datetime(payload.get("next_execution_at")),
        created_at=_deserialize_datetime(payload["created_at"]) or datetime.fromisoformat("1970-01-01T00:00:00+00:00"),
        updated_at=_deserialize_datetime(payload["updated_at"]) or datetime.fromisoformat("1970-01-01T00:00:00+00:00"),
    )


def serialize_event(event: WatchEvent) -> dict[str, Any]:
    """Convert a watch event to a JSON-serializable dictionary."""
    return {
        "event_id": event.event_id,
        "event_type": event.event_type.value,
        "watch_id": event.watch_id,
        "timestamp": _serialize_datetime(event.timestamp),
        "metadata": event.metadata,
    }


def deserialize_event(payload: dict[str, Any]) -> WatchEvent:
    """Restore a watch event from a serialized dictionary."""
    return WatchEvent(
        event_id=str(payload["event_id"]),
        event_type=WatchEventType(str(payload["event_type"])),
        watch_id=str(payload["watch_id"]),
        timestamp=_deserialize_datetime(payload["timestamp"]) or datetime.fromisoformat("1970-01-01T00:00:00+00:00"),
        metadata=dict(payload.get("metadata") or {}),
    )


def dump_store(store: InMemoryWatchPersistence) -> str:
    """Serialize an in-memory store to JSON."""
    payload = {
        "subscriptions": [
            serialize_subscription(item)
            for item in store.list_subscriptions()
        ],
        "events": [serialize_event(item) for item in store.list_events()],
    }
    return json.dumps(payload, sort_keys=True)


def load_store(payload: str | dict[str, Any]) -> InMemoryWatchPersistence:
    """Restore an in-memory store from JSON."""
    store = InMemoryWatchPersistence()
    data = json.loads(payload) if isinstance(payload, str) else payload
    for item in data.get("subscriptions", []):
        store.save_subscription(deserialize_subscription(item))
    for item in data.get("events", []):
        store.append_event(deserialize_event(item))
    return store


def _serialize_protocol(protocol: WatchedProtocol) -> dict[str, Any]:
    return {
        "watch_id": protocol.watch_id,
        "chain_id": protocol.chain_id,
        "root_address": protocol.root_address,
        "protocol_name": protocol.protocol_name,
        "registered_at": _serialize_datetime(protocol.registered_at),
        "metadata": protocol.metadata,
    }


def _deserialize_protocol(payload: dict[str, Any]) -> WatchedProtocol:
    return WatchedProtocol(
        watch_id=str(payload["watch_id"]),
        chain_id=int(payload["chain_id"]),
        root_address=str(payload["root_address"]).lower(),
        protocol_name=str(payload["protocol_name"]),
        registered_at=_deserialize_datetime(payload["registered_at"]) or datetime.fromisoformat("1970-01-01T00:00:00+00:00"),
        metadata=dict(payload.get("metadata") or {}),
    )


def _serialize_configuration(configuration: WatchConfiguration) -> dict[str, Any]:
    return asdict(configuration)


def _deserialize_configuration(payload: dict[str, Any]) -> WatchConfiguration:
    return WatchConfiguration(
        schedule_type=WatchScheduleType(str(payload.get("schedule_type", WatchScheduleType.MANUAL.value))),
        cron_expression=payload.get("cron_expression"),
        timezone=str(payload.get("timezone", "UTC")),
        metadata=dict(payload.get("metadata") or {}),
    )


def _serialize_datetime(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()


def _deserialize_datetime(value: str | None) -> datetime | None:
    if value is None:
        return None
    return datetime.fromisoformat(value)
