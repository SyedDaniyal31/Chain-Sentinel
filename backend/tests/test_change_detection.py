"""Unit tests for snapshot-based change detection (M10.2)."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.blockchain.continuous.change_detection import (
    ChangeDetector,
    ChangeSeverity,
    ChangeType,
    DiffEngine,
    InMemorySnapshotStore,
    SnapshotBuilder,
    change_event_id,
    dump_store,
    load_store,
    serialize_snapshot,
)
from app.blockchain.continuous.protocol_subscription import watch_id

ROOT = "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
PROXY = "0xcccccccccccccccccccccccccccccccccccccccc"
IMPLEMENTATION = "0xdddddddddddddddddddddddddddddddddddddddd"
NEW_IMPLEMENTATION = "0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee"
OWNER = "0x1111111111111111111111111111111111111111"
NEW_OWNER = "0x2222222222222222222222222222222222222222"
GOVERNOR = "0x3333333333333333333333333333333333333333"
TIMELOCK = "0x4444444444444444444444444444444444444444"
TREASURY = "0x5555555555555555555555555555555555555555"
BASELINE_AT = datetime(2026, 6, 13, 12, 0, tzinfo=timezone.utc)
CURRENT_AT = datetime(2026, 6, 13, 13, 0, tzinfo=timezone.utc)
WATCH = watch_id(1, ROOT)


def _snapshot(
    *,
    captured_at: datetime,
    suffix: str = "baseline",
    implementation: str = IMPLEMENTATION,
    owner: str = OWNER,
    liquidity: str = "liquidity:v1",
    dependency: str = "deps:v1",
    runtime: str = "runtime:v1",
    governor: str = GOVERNOR,
    timelock: str = TIMELOCK,
) -> object:
    builder = SnapshotBuilder()
    return builder.build(
        {
            "watch_id": WATCH,
            "chain_id": 1,
            "root_address": ROOT,
            "captured_at": captured_at,
            "snapshot_id": f"{WATCH}:{suffix}",
            "dependency_fingerprint": dependency,
            "liquidity_fingerprint": liquidity,
            "runtime_fingerprint": runtime,
            "contracts": [
                {
                    "address": PROXY,
                    "proxy_implementation": implementation,
                    "owner": owner,
                    "proxy_admin": OWNER,
                    "governor": governor,
                    "timelock": timelock,
                    "treasury": TREASURY,
                    "bytecode_hash": f"bytecode:{suffix}",
                    "abi_hash": f"abi:{suffix}",
                }
            ],
        },
        captured_at=captured_at,
    )


@pytest.fixture
def baseline() -> object:
    return _snapshot(captured_at=BASELINE_AT, suffix="baseline")


@pytest.fixture
def detector() -> ChangeDetector:
    return ChangeDetector()


def test_identical_snapshots_produce_no_changes(detector: ChangeDetector, baseline: object) -> None:
    current = _snapshot(captured_at=CURRENT_AT, suffix="baseline")

    result = detector.detect(baseline, current)

    assert result.unchanged is True
    assert result.changes == ()


def test_implementation_change(detector: ChangeDetector, baseline: object) -> None:
    current = _snapshot(
        captured_at=CURRENT_AT,
        suffix="baseline",
        implementation=NEW_IMPLEMENTATION,
    )

    result = detector.detect(baseline, current)

    assert len(result.changes) == 1
    change = result.changes[0]
    assert change.change_type == ChangeType.IMPLEMENTATION_CHANGED
    assert change.severity == ChangeSeverity.CRITICAL
    assert change.before == IMPLEMENTATION
    assert change.after == NEW_IMPLEMENTATION
    assert change.affected_contracts == (PROXY,)


def test_owner_change(detector: ChangeDetector, baseline: object) -> None:
    current = _snapshot(captured_at=CURRENT_AT, suffix="current", owner=NEW_OWNER)

    result = detector.detect(baseline, current)

    assert any(item.change_type == ChangeType.OWNER_CHANGED for item in result.changes)
    owner_change = next(item for item in result.changes if item.change_type == ChangeType.OWNER_CHANGED)
    assert owner_change.severity == ChangeSeverity.HIGH
    assert owner_change.before == OWNER
    assert owner_change.after == NEW_OWNER


def test_liquidity_change(detector: ChangeDetector, baseline: object) -> None:
    current = _snapshot(
        captured_at=CURRENT_AT,
        suffix="current",
        liquidity="liquidity:v2",
    )

    result = detector.detect(baseline, current)

    change = next(item for item in result.changes if item.change_type == ChangeType.LIQUIDITY_CHANGED)
    assert change.severity == ChangeSeverity.MEDIUM
    assert change.before == "liquidity:v1"
    assert change.after == "liquidity:v2"


def test_dependency_change(detector: ChangeDetector, baseline: object) -> None:
    current = _snapshot(
        captured_at=CURRENT_AT,
        suffix="current",
        dependency="deps:v2",
    )

    result = detector.detect(baseline, current)

    change = next(item for item in result.changes if item.change_type == ChangeType.DEPENDENCY_CHANGED)
    assert change.change_type == ChangeType.DEPENDENCY_CHANGED
    assert change.before == "deps:v1"
    assert change.after == "deps:v2"


def test_deterministic_change_ordering(detector: ChangeDetector, baseline: object) -> None:
    current = _snapshot(
        captured_at=CURRENT_AT,
        suffix="current",
        implementation=NEW_IMPLEMENTATION,
        owner=NEW_OWNER,
        liquidity="liquidity:v2",
        dependency="deps:v2",
    )

    result_one = detector.detect(baseline, current)
    result_two = detector.detect(baseline, current)

    assert [item.event_id for item in result_one.changes] == [item.event_id for item in result_two.changes]
    assert [item.change_type for item in result_one.changes] == [item.change_type for item in result_two.changes]


def test_duplicate_suppression(detector: ChangeDetector, baseline: object) -> None:
    current = _snapshot(
        captured_at=CURRENT_AT,
        suffix="baseline",
        implementation=NEW_IMPLEMENTATION,
    )
    raw_changes = DiffEngine().diff(baseline, current)
    implementation_changes = tuple(
        item for item in raw_changes if item.change_type == ChangeType.IMPLEMENTATION_CHANGED
    )
    duplicate = implementation_changes + implementation_changes

    events = detector._build_events(
        watch_id=WATCH,
        raw_changes=duplicate,
        timestamp=CURRENT_AT,
    )

    assert len(events) == 1


def test_detect_from_store(detector: ChangeDetector, baseline: object) -> None:
    store = InMemorySnapshotStore()
    store.save_baseline(baseline)
    current = _snapshot(captured_at=CURRENT_AT, suffix="current", owner=NEW_OWNER)
    store.save_current(current)
    bound_detector = ChangeDetector(snapshot_store=store)

    result = bound_detector.detect_from_store(WATCH, current, detected_at=CURRENT_AT)

    assert result.watch_id == WATCH
    assert any(item.change_type == ChangeType.OWNER_CHANGED for item in result.changes)


def test_snapshot_store_serialization(baseline: object) -> None:
    store = InMemorySnapshotStore()
    store.save_baseline(baseline)
    current = _snapshot(captured_at=CURRENT_AT, suffix="current")
    store.save_current(current)

    restored = load_store(dump_store(store))

    assert restored.get_baseline(WATCH) is not None
    assert restored.get_current(WATCH) is not None
    assert restored.get_baseline(WATCH).contracts[0].proxy_implementation == IMPLEMENTATION


def test_change_event_id_is_stable() -> None:
    first = change_event_id(
        watch_id=WATCH,
        change_type=ChangeType.OWNER_CHANGED,
        before=OWNER,
        after=NEW_OWNER,
        affected_contracts=(PROXY,),
    )
    second = change_event_id(
        watch_id=WATCH,
        change_type=ChangeType.OWNER_CHANGED,
        before=OWNER,
        after=NEW_OWNER,
        affected_contracts=(PROXY,),
    )

    assert first == second


def test_snapshot_serialization_roundtrip(baseline: object) -> None:
    payload = serialize_snapshot(baseline)
    restored = SnapshotBuilder().build(payload)

    assert restored.watch_id == baseline.watch_id
    assert restored.contracts[0].owner == OWNER
