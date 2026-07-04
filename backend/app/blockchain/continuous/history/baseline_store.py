"""Immutable baseline snapshot storage (M10.6)."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Any

from app.blockchain.continuous.change_detection.models import ProtocolSnapshot
from app.blockchain.continuous.change_detection.snapshot_store import (
    deserialize_snapshot,
    serialize_snapshot,
)


class BaselineStore(ABC):
    """Abstract storage for immutable per-watch baseline snapshots."""

    @abstractmethod
    def set_baseline(self, snapshot: ProtocolSnapshot) -> bool:
        """Persist the baseline snapshot. Returns False if baseline already exists."""

    @abstractmethod
    def get_baseline(self, watch_id: str) -> ProtocolSnapshot | None:
        """Load the immutable baseline snapshot."""

    @abstractmethod
    def has_baseline(self, watch_id: str) -> bool:
        """Return whether a baseline snapshot exists for the watch."""


class InMemoryBaselineStore(BaselineStore):
    """In-memory baseline store for tests and development."""

    def __init__(self) -> None:
        self._baselines: dict[str, ProtocolSnapshot] = {}

    def set_baseline(self, snapshot: ProtocolSnapshot) -> bool:
        if snapshot.watch_id in self._baselines:
            return False
        self._baselines[snapshot.watch_id] = snapshot
        return True

    def get_baseline(self, watch_id: str) -> ProtocolSnapshot | None:
        return self._baselines.get(watch_id)

    def has_baseline(self, watch_id: str) -> bool:
        return watch_id in self._baselines


def dump_baseline_store(store: InMemoryBaselineStore) -> str:
    """Serialize an in-memory baseline store to JSON."""
    payload = {
        key: serialize_snapshot(value)
        for key, value in sorted(store._baselines.items())
    }
    return json.dumps(payload, sort_keys=True)


def load_baseline_store(payload: str | dict[str, Any]) -> InMemoryBaselineStore:
    """Restore an in-memory baseline store from JSON."""
    store = InMemoryBaselineStore()
    data = json.loads(payload) if isinstance(payload, str) else payload
    for item in data.values():
        snapshot = deserialize_snapshot(item)
        store.set_baseline(snapshot)
    return store
