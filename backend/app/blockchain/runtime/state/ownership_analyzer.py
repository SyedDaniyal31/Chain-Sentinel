"""Ownership and admin transition analysis (M9.3)."""

from __future__ import annotations

from app.blockchain.runtime.state.event_state_mapper import EventStateMapper
from app.blockchain.runtime.state.models import (
    OwnershipChange,
    OwnershipRole,
    RawStateTransition,
    StorageDiff,
    StorageSlotKind,
)


class OwnershipAnalyzer:
    """Detect owner, proxy admin, governor, and treasury transitions."""

    def __init__(self, event_mapper: EventStateMapper | None = None) -> None:
        self._event_mapper = event_mapper or EventStateMapper()

    def analyze(
        self,
        transition: RawStateTransition,
        storage_changes: tuple[StorageDiff, ...],
    ) -> tuple[OwnershipChange, ...]:
        changes: list[OwnershipChange] = []

        for storage in storage_changes:
            role = _role_from_storage(storage.slot_kind)
            if role is None:
                continue
            if storage.before_address == storage.after_address:
                continue
            changes.append(
                OwnershipChange(
                    role=role,
                    contract_address=storage.contract_address,
                    before_address=storage.before_address,
                    after_address=storage.after_address,
                )
            )

        for event in self._event_mapper.map_logs(transition.logs):
            if event.event_kind.value == "ownership_transferred":
                changes.append(
                    OwnershipChange(
                        role=OwnershipRole.OWNER,
                        contract_address=event.contract_address.lower(),
                        before_address=str(event.metadata.get("previous_owner")).lower()
                        if event.metadata.get("previous_owner")
                        else None,
                        after_address=str(event.metadata.get("new_owner")).lower()
                        if event.metadata.get("new_owner")
                        else None,
                    )
                )
            elif event.event_kind.value == "role_granted":
                role_name = str(event.metadata.get("role", "")).lower()
                mapped_role = _map_role_name(role_name)
                if mapped_role is None:
                    continue
                changes.append(
                    OwnershipChange(
                        role=mapped_role,
                        contract_address=event.contract_address.lower(),
                        before_address=None,
                        after_address=str(event.metadata.get("account", "")).lower() or None,
                    )
                )

        return tuple(sorted(_dedupe_ownership(changes), key=_ownership_sort_key))


def _role_from_storage(slot_kind: StorageSlotKind) -> OwnershipRole | None:
    mapping = {
        StorageSlotKind.IMPLEMENTATION: None,
        StorageSlotKind.PROXY_ADMIN: OwnershipRole.PROXY_ADMIN,
        StorageSlotKind.OWNER: OwnershipRole.OWNER,
        StorageSlotKind.TIMELOCK: OwnershipRole.GOVERNOR,
    }
    return mapping.get(slot_kind)


def _map_role_name(role_name: str) -> OwnershipRole | None:
    if "admin" in role_name:
        return OwnershipRole.PROXY_ADMIN
    if "governor" in role_name or "timelock" in role_name:
        return OwnershipRole.GOVERNOR
    if "treasury" in role_name:
        return OwnershipRole.TREASURY
    if "multisig" in role_name:
        return OwnershipRole.MULTISIG
    if "owner" in role_name:
        return OwnershipRole.OWNER
    return None


def _dedupe_ownership(changes: list[OwnershipChange]) -> list[OwnershipChange]:
    seen: set[tuple[str, str, str | None, str | None]] = set()
    unique: list[OwnershipChange] = []
    for change in changes:
        key = (
            change.role.value,
            change.contract_address,
            change.before_address,
            change.after_address,
        )
        if key in seen:
            continue
        seen.add(key)
        unique.append(change)
    return unique


def _ownership_sort_key(item: OwnershipChange) -> tuple[str, str]:
    return (item.role.value, item.contract_address)
