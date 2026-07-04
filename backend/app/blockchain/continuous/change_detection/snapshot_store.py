"""Protocol snapshot persistence (M10.2)."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from app.blockchain.continuous.change_detection.models import ContractSnapshot, ProtocolSnapshot
from app.blockchain.continuous.change_detection.snapshot_builder import SnapshotBuilder


class SnapshotStore(ABC):
    """Abstract storage for baseline and current protocol snapshots."""

    @abstractmethod
    def save_baseline(self, snapshot: ProtocolSnapshot) -> None:
        """Persist the baseline snapshot for a watch."""

    @abstractmethod
    def save_current(self, snapshot: ProtocolSnapshot) -> None:
        """Persist the latest current snapshot for a watch."""

    @abstractmethod
    def get_baseline(self, watch_id: str) -> ProtocolSnapshot | None:
        """Load the baseline snapshot."""

    @abstractmethod
    def get_current(self, watch_id: str) -> ProtocolSnapshot | None:
        """Load the latest current snapshot."""

    @abstractmethod
    def delete_watch(self, watch_id: str) -> None:
        """Remove stored snapshots for a watch."""


class InMemorySnapshotStore(SnapshotStore):
    """In-memory snapshot store for tests and development."""

    def __init__(self) -> None:
        self._baselines: dict[str, ProtocolSnapshot] = {}
        self._current: dict[str, ProtocolSnapshot] = {}

    def save_baseline(self, snapshot: ProtocolSnapshot) -> None:
        self._baselines[snapshot.watch_id] = snapshot

    def save_current(self, snapshot: ProtocolSnapshot) -> None:
        self._current[snapshot.watch_id] = snapshot

    def get_baseline(self, watch_id: str) -> ProtocolSnapshot | None:
        return self._baselines.get(watch_id)

    def get_current(self, watch_id: str) -> ProtocolSnapshot | None:
        return self._current.get(watch_id)

    def delete_watch(self, watch_id: str) -> None:
        self._baselines.pop(watch_id, None)
        self._current.pop(watch_id, None)


def serialize_snapshot(snapshot: ProtocolSnapshot) -> dict[str, Any]:
    """Convert a protocol snapshot to JSON-serializable data."""
    return {
        "snapshot_id": snapshot.snapshot_id,
        "watch_id": snapshot.watch_id,
        "chain_id": snapshot.chain_id,
        "root_address": snapshot.root_address,
        "captured_at": snapshot.captured_at.isoformat(),
        "contracts": [_serialize_contract(item) for item in snapshot.contracts],
        "dependency_fingerprint": snapshot.dependency_fingerprint,
        "liquidity_fingerprint": snapshot.liquidity_fingerprint,
        "runtime_fingerprint": snapshot.runtime_fingerprint,
        "metadata": snapshot.metadata,
    }


def deserialize_snapshot(payload: dict[str, Any]) -> ProtocolSnapshot:
    """Restore a protocol snapshot from serialized data."""
    return SnapshotBuilder().build(payload)


def dump_store(store: InMemorySnapshotStore) -> str:
    """Serialize an in-memory snapshot store to JSON."""
    payload = {
        "baselines": {
            key: serialize_snapshot(value)
            for key, value in sorted(store._baselines.items())
        },
        "current": {
            key: serialize_snapshot(value)
            for key, value in sorted(store._current.items())
        },
    }
    return json.dumps(payload, sort_keys=True)


def load_store(payload: str | dict[str, Any]) -> InMemorySnapshotStore:
    """Restore an in-memory snapshot store from JSON."""
    store = InMemorySnapshotStore()
    data = json.loads(payload) if isinstance(payload, str) else payload
    for item in data.get("baselines", {}).values():
        store.save_baseline(deserialize_snapshot(item))
    for item in data.get("current", {}).values():
        store.save_current(deserialize_snapshot(item))
    return store


def _serialize_contract(contract: ContractSnapshot) -> dict[str, Any]:
    return {
        "address": contract.address,
        "proxy_implementation": contract.proxy_implementation,
        "owner": contract.owner,
        "proxy_admin": contract.proxy_admin,
        "timelock": contract.timelock,
        "governor": contract.governor,
        "treasury": contract.treasury,
        "bytecode_hash": contract.bytecode_hash,
        "abi_hash": contract.abi_hash,
        "metadata": contract.metadata,
    }
