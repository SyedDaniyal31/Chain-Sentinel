"""Snapshot diff engine (M10.2)."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime

from app.blockchain.continuous.change_detection.models import ChangeType, ContractSnapshot, ProtocolSnapshot
from app.blockchain.continuous.change_detection.snapshot import contract_index, ensure_protocol_compatibility


@dataclass(frozen=True, slots=True)
class RawChange:
    """Intermediate diff before classification."""

    change_type: ChangeType
    before: str | None
    after: str | None
    affected_contracts: tuple[str, ...]


class DiffEngine:
    """Compare baseline and current protocol snapshots."""

    CONTRACT_FIELDS: tuple[tuple[str, ChangeType], ...] = (
        ("proxy_implementation", ChangeType.IMPLEMENTATION_CHANGED),
        ("owner", ChangeType.OWNER_CHANGED),
        ("proxy_admin", ChangeType.PROXY_ADMIN_CHANGED),
        ("bytecode_hash", ChangeType.BYTECODE_CHANGED),
        ("treasury", ChangeType.TREASURY_CHANGED),
    )
    GOVERNANCE_FIELDS: tuple[str, ...] = ("governor", "timelock")

    def diff(
        self,
        baseline: ProtocolSnapshot,
        current: ProtocolSnapshot,
    ) -> tuple[RawChange, ...]:
        ensure_protocol_compatibility(baseline, current)
        changes: list[RawChange] = []
        baseline_contracts = contract_index(baseline.contracts)
        current_contracts = contract_index(current.contracts)
        addresses = sorted(set(baseline_contracts) | set(current_contracts))

        for address in addresses:
            before_contract = baseline_contracts.get(address)
            after_contract = current_contracts.get(address)
            changes.extend(self._diff_contract(before_contract, after_contract, address))

        changes.extend(self._diff_protocol_field(
            ChangeType.DEPENDENCY_CHANGED,
            baseline.dependency_fingerprint,
            current.dependency_fingerprint,
            addresses,
        ))
        changes.extend(self._diff_protocol_field(
            ChangeType.LIQUIDITY_CHANGED,
            baseline.liquidity_fingerprint,
            current.liquidity_fingerprint,
            addresses,
        ))
        changes.extend(self._diff_protocol_field(
            ChangeType.RUNTIME_FINGERPRINT_CHANGED,
            baseline.runtime_fingerprint,
            current.runtime_fingerprint,
            addresses,
        ))

        return tuple(sorted(changes, key=_raw_change_sort_key))

    def _diff_contract(
        self,
        before: ContractSnapshot | None,
        after: ContractSnapshot | None,
        address: str,
    ) -> list[RawChange]:
        changes: list[RawChange] = []
        for field_name, change_type in self.CONTRACT_FIELDS:
            before_value = getattr(before, field_name, None) if before else None
            after_value = getattr(after, field_name, None) if after else None
            if before_value == after_value:
                continue
            changes.append(
                RawChange(
                    change_type=change_type,
                    before=before_value,
                    after=after_value,
                    affected_contracts=(address,),
                )
            )

        governance_before = _governance_value(before)
        governance_after = _governance_value(after)
        if governance_before != governance_after:
            changes.append(
                RawChange(
                    change_type=ChangeType.GOVERNANCE_CHANGED,
                    before=governance_before,
                    after=governance_after,
                    affected_contracts=(address,),
                )
            )
        return changes

    def _diff_protocol_field(
        self,
        change_type: ChangeType,
        before: str,
        after: str,
        addresses: list[str],
    ) -> list[RawChange]:
        if before == after:
            return []
        return [
            RawChange(
                change_type=change_type,
                before=before or None,
                after=after or None,
                affected_contracts=tuple(addresses),
            )
        ]


def change_event_id(
    *,
    watch_id: str,
    change_type: ChangeType,
    before: str | None,
    after: str | None,
    affected_contracts: tuple[str, ...],
) -> str:
    """Build a deterministic change event identifier for deduplication."""
    payload = "|".join(
        [
            watch_id,
            change_type.value,
            before or "",
            after or "",
            ",".join(affected_contracts),
        ]
    )
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
    return f"{watch_id}:{change_type.value}:{digest}"


def _governance_value(contract: ContractSnapshot | None) -> str | None:
    if contract is None:
        return None
    return f"governor={contract.governor or ''};timelock={contract.timelock or ''}"


def _raw_change_sort_key(item: RawChange) -> tuple[str, str, str, str]:
    return (
        item.change_type.value,
        ",".join(item.affected_contracts),
        item.before or "",
        item.after or "",
    )
