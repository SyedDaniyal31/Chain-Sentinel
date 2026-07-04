"""Aggregate normalized state transition diffs (M9.3)."""

from __future__ import annotations

from dataclasses import dataclass

from app.blockchain.runtime.state.allowance_analyzer import AllowanceAnalyzer
from app.blockchain.runtime.state.balance_analyzer import BalanceAnalyzer
from app.blockchain.runtime.state.models import (
    AllowanceChange,
    BalanceChange,
    MappedStateEvent,
    OwnershipChange,
    RawStateTransition,
    StorageDiff,
    SupplyChange,
)
from app.blockchain.runtime.state.ownership_analyzer import OwnershipAnalyzer
from app.blockchain.runtime.state.storage_analyzer import StorageAnalyzer
from app.blockchain.runtime.state.supply_analyzer import SupplyAnalyzer
from app.blockchain.runtime.state.event_state_mapper import EventStateMapper


@dataclass(frozen=True, slots=True)
class StateDiffBundle:
    """Normalized state diff bundle produced from a raw transition."""

    storage_changes: tuple[StorageDiff, ...]
    balance_changes: tuple[BalanceChange, ...]
    allowance_changes: tuple[AllowanceChange, ...]
    ownership_changes: tuple[OwnershipChange, ...]
    supply_changes: tuple[SupplyChange, ...]
    mapped_state_events: tuple[MappedStateEvent, ...]


class StateDiffBuilder:
    """Build deterministic semantic state diffs from normalized provider data."""

    def __init__(
        self,
        storage_analyzer: StorageAnalyzer | None = None,
        balance_analyzer: BalanceAnalyzer | None = None,
        allowance_analyzer: AllowanceAnalyzer | None = None,
        ownership_analyzer: OwnershipAnalyzer | None = None,
        supply_analyzer: SupplyAnalyzer | None = None,
        event_mapper: EventStateMapper | None = None,
    ) -> None:
        self._event_mapper = event_mapper or EventStateMapper()
        self._storage_analyzer = storage_analyzer or StorageAnalyzer()
        self._balance_analyzer = balance_analyzer or BalanceAnalyzer(self._event_mapper)
        self._allowance_analyzer = allowance_analyzer or AllowanceAnalyzer(self._event_mapper)
        self._ownership_analyzer = ownership_analyzer or OwnershipAnalyzer(self._event_mapper)
        self._supply_analyzer = supply_analyzer or SupplyAnalyzer()

    def build(self, transition: RawStateTransition) -> StateDiffBundle:
        storage_changes = self._storage_analyzer.analyze(transition)
        mapped_state_events = self._event_mapper.map_logs(transition.logs)
        balance_changes = self._balance_analyzer.analyze(transition)
        allowance_changes = self._allowance_analyzer.analyze(transition)
        ownership_changes = self._ownership_analyzer.analyze(transition, storage_changes)
        supply_changes = self._supply_analyzer.analyze(transition)
        return StateDiffBundle(
            storage_changes=storage_changes,
            balance_changes=balance_changes,
            allowance_changes=allowance_changes,
            ownership_changes=ownership_changes,
            supply_changes=supply_changes,
            mapped_state_events=mapped_state_events,
        )
