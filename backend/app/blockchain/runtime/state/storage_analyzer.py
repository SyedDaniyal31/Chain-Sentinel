"""Storage slot transition analysis (M9.3)."""

from __future__ import annotations

from app.blockchain.eip1967 import EIP1967_ADMIN_SLOT, EIP1967_BEACON_SLOT, EIP1967_IMPLEMENTATION_SLOT
from app.blockchain.runtime.state.models import RawStateTransition, StorageDiff, StorageSlotKind


class StorageAnalyzer:
    """Detect semantic storage slot changes from normalized state diffs."""

    KNOWN_SLOTS: dict[str, StorageSlotKind] = {
        EIP1967_IMPLEMENTATION_SLOT.lower(): StorageSlotKind.IMPLEMENTATION,
        EIP1967_ADMIN_SLOT.lower(): StorageSlotKind.PROXY_ADMIN,
        EIP1967_BEACON_SLOT.lower(): StorageSlotKind.BEACON,
        "0x0000000000000000000000000000000000000000000000000000000000000000": StorageSlotKind.OWNER,
        "0x0000000000000000000000000000000000000000000000000000000000000001": StorageSlotKind.ACCESS_CONTROL_ROLE,
        "0x0000000000000000000000000000000000000000000000000000000000000002": StorageSlotKind.TIMELOCK,
    }

    def analyze(self, transition: RawStateTransition) -> tuple[StorageDiff, ...]:
        changes: list[StorageDiff] = []
        for diff in transition.storage_diffs:
            if diff.before == diff.after:
                continue
            slot_kind = self.KNOWN_SLOTS.get(diff.slot.lower(), StorageSlotKind.ARBITRARY)
            changes.append(
                StorageDiff(
                    contract_address=diff.contract_address.lower(),
                    slot=diff.slot.lower(),
                    slot_kind=slot_kind,
                    before=diff.before.lower(),
                    after=diff.after.lower(),
                    before_address=_extract_address(diff.before),
                    after_address=_extract_address(diff.after),
                )
            )
        return tuple(sorted(changes, key=_storage_sort_key))


def _extract_address(word: str) -> str | None:
    normalized = word.lower().removeprefix("0x")
    if len(normalized) < 40:
        return None
    address = "0x" + normalized[-40:]
    if address == "0x0000000000000000000000000000000000000000":
        return None
    return address


def _storage_sort_key(item: StorageDiff) -> tuple[str, str]:
    return (item.contract_address, item.slot)
