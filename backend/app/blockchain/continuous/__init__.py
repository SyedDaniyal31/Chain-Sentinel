"""Continuous protocol monitoring platform (M10.1)."""

from app.blockchain.continuous.models import (
    WatchConfiguration,
    WatchEvent,
    WatchEventType,
    WatchScheduleType,
    WatchStatus,
    WatchSubscription,
    WatchedProtocol,
)
from app.blockchain.continuous.persistence import (
    InMemoryWatchPersistence,
    WatchPersistenceStore,
    deserialize_event,
    deserialize_subscription,
    dump_store,
    load_store,
    serialize_event,
    serialize_subscription,
)
from app.blockchain.continuous.protocol_subscription import (
    build_subscription,
    build_watched_protocol,
    event_id,
    merge_configuration,
    watch_id,
)
from app.blockchain.continuous.scheduler import WatchScheduler
from app.blockchain.continuous.watch_manager import WatchManager
from app.blockchain.continuous.watch_registry import DuplicateWatchError, WatchNotFoundError, WatchRegistry

__all__ = [
    "DuplicateWatchError",
    "InMemoryWatchPersistence",
    "WatchConfiguration",
    "WatchEvent",
    "WatchEventType",
    "WatchManager",
    "WatchNotFoundError",
    "WatchPersistenceStore",
    "WatchRegistry",
    "WatchScheduleType",
    "WatchScheduler",
    "WatchStatus",
    "WatchSubscription",
    "WatchedProtocol",
    "build_subscription",
    "build_watched_protocol",
    "deserialize_event",
    "deserialize_subscription",
    "dump_store",
    "event_id",
    "load_store",
    "merge_configuration",
    "serialize_event",
    "serialize_subscription",
    "watch_id",
]
