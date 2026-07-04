"""Snapshot-based protocol change detection (M10.2)."""

from app.blockchain.continuous.change_detection.change_classifier import ChangeClassifier
from app.blockchain.continuous.change_detection.change_detector import ChangeDetector
from app.blockchain.continuous.change_detection.diff_engine import DiffEngine, RawChange, change_event_id
from app.blockchain.continuous.change_detection.models import (
    ChangeDetectionResult,
    ChangeEvent,
    ChangeSeverity,
    ChangeType,
    ContractSnapshot,
    ProtocolSnapshot,
)
from app.blockchain.continuous.change_detection.snapshot import (
    contract_addresses,
    contract_index,
    ensure_protocol_compatibility,
    normalize_address,
    snapshot_id,
    utc_now,
)
from app.blockchain.continuous.change_detection.snapshot_builder import SnapshotBuilder
from app.blockchain.continuous.change_detection.snapshot_store import (
    InMemorySnapshotStore,
    SnapshotStore,
    deserialize_snapshot,
    dump_store,
    load_store,
    serialize_snapshot,
)

__all__ = [
    "ChangeClassifier",
    "ChangeDetectionResult",
    "ChangeDetector",
    "ChangeEvent",
    "ChangeSeverity",
    "ChangeType",
    "ContractSnapshot",
    "DiffEngine",
    "InMemorySnapshotStore",
    "ProtocolSnapshot",
    "RawChange",
    "SnapshotBuilder",
    "SnapshotStore",
    "change_event_id",
    "contract_addresses",
    "contract_index",
    "deserialize_snapshot",
    "dump_store",
    "ensure_protocol_compatibility",
    "load_store",
    "normalize_address",
    "serialize_snapshot",
    "snapshot_id",
    "utc_now",
]
