"""Unit tests for continuous watch registry (M10.1)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.blockchain.continuous import (
    DuplicateWatchError,
    InMemoryWatchPersistence,
    WatchConfiguration,
    WatchEventType,
    WatchManager,
    WatchNotFoundError,
    WatchRegistry,
    WatchScheduleType,
    WatchScheduler,
    WatchStatus,
    dump_store,
    load_store,
    serialize_subscription,
    watch_id,
)

ROOT = "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
OTHER = "0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
NOW = datetime(2026, 6, 13, 12, 0, tzinfo=timezone.utc)
BASELINE = {"scan_id": 1, "risk_score": "12.50", "completed_at": NOW.isoformat()}


@pytest.fixture
def persistence() -> InMemoryWatchPersistence:
    return InMemoryWatchPersistence()


@pytest.fixture
def registry(persistence: InMemoryWatchPersistence) -> WatchRegistry:
    return WatchRegistry(persistence=persistence)


@pytest.fixture
def manager(registry: WatchRegistry) -> WatchManager:
    return WatchManager(registry=registry)


def test_register_protocol(registry: WatchRegistry) -> None:
    subscription = registry.register(
        chain_id=1,
        root_address=ROOT,
        protocol_name="test-protocol",
        configuration=WatchConfiguration(schedule_type=WatchScheduleType.DAILY),
        baseline_scan=BASELINE,
        now=NOW,
    )

    assert subscription.protocol.watch_id == watch_id(1, ROOT)
    assert subscription.protocol.protocol_name == "test-protocol"
    assert subscription.configuration.schedule_type == WatchScheduleType.DAILY
    assert subscription.baseline_scan == BASELINE
    assert subscription.status == WatchStatus.ENABLED
    assert subscription.next_execution_at == NOW + timedelta(days=1)


def test_duplicate_registration_prevented(registry: WatchRegistry) -> None:
    registry.register(
        chain_id=1,
        root_address=ROOT,
        protocol_name="test-protocol",
        now=NOW,
    )

    with pytest.raises(DuplicateWatchError):
        registry.register(
            chain_id=1,
            root_address=ROOT.upper(),
            protocol_name="duplicate",
            now=NOW,
        )


def test_unregister_protocol(registry: WatchRegistry) -> None:
    subscription = registry.register(
        chain_id=1,
        root_address=ROOT,
        protocol_name="test-protocol",
        now=NOW,
    )

    assert registry.unregister(subscription.protocol.watch_id) is True
    assert registry.get_watch(subscription.protocol.watch_id) is None
    events = registry.list_events(subscription.protocol.watch_id)
    assert any(event.event_type == WatchEventType.UNREGISTERED for event in events)


def test_update_configuration(registry: WatchRegistry) -> None:
    subscription = registry.register(
        chain_id=1,
        root_address=ROOT,
        protocol_name="test-protocol",
        configuration=WatchConfiguration(schedule_type=WatchScheduleType.MANUAL),
        now=NOW,
    )

    updated = registry.update_configuration(
        subscription.protocol.watch_id,
        WatchConfiguration(schedule_type=WatchScheduleType.HOURLY),
        now=NOW,
    )

    assert updated.configuration.schedule_type == WatchScheduleType.HOURLY
    assert updated.next_execution_at == NOW + timedelta(hours=1)
    events = registry.list_events(subscription.protocol.watch_id)
    assert any(event.event_type == WatchEventType.CONFIG_UPDATED for event in events)


def test_list_watches_deterministic(registry: WatchRegistry) -> None:
    registry.register(chain_id=1, root_address=OTHER, protocol_name="b", now=NOW)
    registry.register(chain_id=1, root_address=ROOT, protocol_name="a", now=NOW)

    watches = registry.list_watches()
    assert [item.protocol.root_address for item in watches] == sorted([ROOT, OTHER])


def test_enable_disable_pause_resume(manager: WatchManager, registry: WatchRegistry) -> None:
    subscription = registry.register(
        chain_id=1,
        root_address=ROOT,
        protocol_name="test-protocol",
        configuration=WatchConfiguration(schedule_type=WatchScheduleType.HOURLY),
        now=NOW,
    )
    watch = subscription.protocol.watch_id

    paused = manager.pause(watch, now=NOW)
    assert paused.status == WatchStatus.PAUSED
    assert paused.next_execution_at is None

    resumed = manager.resume(watch, now=NOW)
    assert resumed.status == WatchStatus.ENABLED
    assert resumed.next_execution_at == NOW + timedelta(hours=1)

    disabled = manager.disable(watch, now=NOW)
    assert disabled.status == WatchStatus.DISABLED
    assert disabled.next_execution_at is None

    enabled = manager.enable(watch, now=NOW)
    assert enabled.status == WatchStatus.ENABLED
    assert enabled.next_execution_at == NOW + timedelta(hours=1)


def test_delete_watch(manager: WatchManager, registry: WatchRegistry) -> None:
    subscription = registry.register(
        chain_id=1,
        root_address=ROOT,
        protocol_name="test-protocol",
        now=NOW,
    )
    watch = subscription.protocol.watch_id

    assert manager.delete(watch) is True
    assert registry.get_watch(watch) is None
    events = registry.list_events(watch)
    assert any(event.event_type == WatchEventType.DELETED for event in events)


def test_scheduler_manual_has_no_next_execution() -> None:
    scheduler = WatchScheduler()
    config = WatchConfiguration(schedule_type=WatchScheduleType.MANUAL)

    assert scheduler.compute_next_execution(config, reference_time=NOW) is None


@pytest.mark.parametrize(
    ("schedule_type", "delta"),
    [
        (WatchScheduleType.HOURLY, timedelta(hours=1)),
        (WatchScheduleType.DAILY, timedelta(days=1)),
        (WatchScheduleType.WEEKLY, timedelta(weeks=1)),
    ],
)
def test_scheduler_intervals(schedule_type: WatchScheduleType, delta: timedelta) -> None:
    scheduler = WatchScheduler()
    config = WatchConfiguration(schedule_type=schedule_type)

    assert scheduler.compute_next_execution(config, reference_time=NOW) == NOW + delta


def test_record_execution_updates_persistence(registry: WatchRegistry) -> None:
    subscription = registry.register(
        chain_id=1,
        root_address=ROOT,
        protocol_name="test-protocol",
        configuration=WatchConfiguration(schedule_type=WatchScheduleType.HOURLY),
        baseline_scan=BASELINE,
        now=NOW,
    )
    executed_at = NOW + timedelta(minutes=5)
    snapshot = {"scan_id": 2, "risk_score": "15.00"}

    updated = registry.record_execution(
        subscription.protocol.watch_id,
        executed_at=executed_at,
        scan_snapshot=snapshot,
    )

    assert updated.last_execution_at == executed_at
    assert updated.baseline_scan == BASELINE
    assert updated.next_execution_at == executed_at + timedelta(hours=1)


def test_persistence_roundtrip(registry: WatchRegistry, persistence: InMemoryWatchPersistence) -> None:
    registry.register(
        chain_id=1,
        root_address=ROOT,
        protocol_name="test-protocol",
        configuration=WatchConfiguration(schedule_type=WatchScheduleType.DAILY),
        baseline_scan=BASELINE,
        now=NOW,
    )

    restored = load_store(dump_store(persistence))
    watches = restored.list_subscriptions()

    assert len(watches) == 1
    assert watches[0].protocol.root_address == ROOT
    assert watches[0].baseline_scan == BASELINE
    assert watches[0].configuration.schedule_type == WatchScheduleType.DAILY


def test_subscription_serialization(registry: WatchRegistry) -> None:
    subscription = registry.register(
        chain_id=1,
        root_address=ROOT,
        protocol_name="test-protocol",
        baseline_scan=BASELINE,
        now=NOW,
    )

    payload = serialize_subscription(subscription)
    assert payload["protocol"]["root_address"] == ROOT
    assert payload["baseline_scan"] == BASELINE
    assert payload["status"] == WatchStatus.ENABLED.value


def test_scheduler_is_due(registry: WatchRegistry) -> None:
    subscription = registry.register(
        chain_id=1,
        root_address=ROOT,
        protocol_name="test-protocol",
        configuration=WatchConfiguration(schedule_type=WatchScheduleType.HOURLY),
        now=NOW,
    )
    scheduler = WatchScheduler()

    assert scheduler.is_due(subscription, now=NOW) is False
    assert scheduler.is_due(subscription, now=NOW + timedelta(hours=1)) is True
