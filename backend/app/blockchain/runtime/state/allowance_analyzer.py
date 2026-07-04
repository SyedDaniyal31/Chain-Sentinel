"""Allowance transition analysis (M9.3)."""

from __future__ import annotations

from app.blockchain.runtime.state.event_state_mapper import EventStateMapper
from app.blockchain.runtime.state.models import AllowanceChange, AllowanceChangeKind, RawStateTransition

MAX_UINT256 = (1 << 256) - 1
LARGE_ALLOWANCE_THRESHOLD = 10**30


class AllowanceAnalyzer:
    """Detect allowance grants, revocations, and unlimited approvals."""

    def __init__(self, event_mapper: EventStateMapper | None = None) -> None:
        self._event_mapper = event_mapper or EventStateMapper()

    def analyze(self, transition: RawStateTransition) -> tuple[AllowanceChange, ...]:
        changes: list[AllowanceChange] = []

        for diff in transition.allowance_diffs:
            changes.append(_build_allowance_change(diff.before, diff.after, diff))

        for event in self._event_mapper.map_logs(transition.logs):
            if event.event_kind.value != "approval":
                continue
            before = int(event.metadata.get("before", 0))
            after = int(event.metadata.get("value", 0))
            changes.append(
                AllowanceChange(
                    kind=_allowance_kind(before, after),
                    token_address=event.contract_address.lower(),
                    owner_address=str(event.metadata.get("owner", "")).lower(),
                    spender_address=str(event.metadata.get("spender", "")).lower(),
                    before=before,
                    after=after,
                    is_unlimited=_is_unlimited(after),
                )
            )

        return tuple(sorted(_dedupe_allowances(changes), key=_allowance_sort_key))


def _build_allowance_change(before: int, after: int, diff: object) -> AllowanceChange:
    return AllowanceChange(
        kind=_allowance_kind(before, after),
        token_address=getattr(diff, "token_address").lower(),
        owner_address=getattr(diff, "owner_address").lower(),
        spender_address=getattr(diff, "spender_address").lower(),
        before=before,
        after=after,
        is_unlimited=_is_unlimited(after),
    )


def _allowance_kind(before: int, after: int) -> AllowanceChangeKind:
    if after >= MAX_UINT256 or after >= LARGE_ALLOWANCE_THRESHOLD:
        return AllowanceChangeKind.UNLIMITED
    if after == 0 and before > 0:
        return AllowanceChangeKind.REVOKE
    if after > before:
        return AllowanceChangeKind.INCREASE
    if after < before:
        return AllowanceChangeKind.DECREASE
    return AllowanceChangeKind.APPROVE


def _is_unlimited(value: int) -> bool:
    return value >= MAX_UINT256 or value >= LARGE_ALLOWANCE_THRESHOLD


def _dedupe_allowances(changes: list[AllowanceChange]) -> list[AllowanceChange]:
    seen: set[tuple[str, str, str]] = set()
    unique: list[AllowanceChange] = []
    for change in changes:
        key = (change.token_address, change.owner_address, change.spender_address)
        if key in seen:
            continue
        seen.add(key)
        unique.append(change)
    return unique


def _allowance_sort_key(item: AllowanceChange) -> tuple[str, str, str]:
    return (item.token_address, item.owner_address, item.spender_address)
