"""Token supply transition analysis (M9.3)."""

from __future__ import annotations

from app.blockchain.runtime.state.models import RawStateTransition, SupplyChange, SupplyChangeKind

LARGE_SUPPLY_DELTA = 10**24


class SupplyAnalyzer:
    """Detect mint, burn, and supply inflation/reduction."""

    def analyze(self, transition: RawStateTransition) -> tuple[SupplyChange, ...]:
        changes: list[SupplyChange] = []
        for diff in transition.supply_diffs:
            if diff.before == diff.after:
                continue
            delta = diff.after - diff.before
            changes.append(
                SupplyChange(
                    kind=_classify_supply_change(delta),
                    token_address=diff.token_address.lower(),
                    before=diff.before,
                    after=diff.after,
                    delta=delta,
                )
            )
        return tuple(sorted(changes, key=lambda item: (item.token_address, item.kind.value)))


def _classify_supply_change(delta: int) -> SupplyChangeKind:
    if delta > 0 and delta >= LARGE_SUPPLY_DELTA:
        return SupplyChangeKind.INFLATION
    if delta > 0:
        return SupplyChangeKind.MINT
    if delta < 0 and abs(delta) >= LARGE_SUPPLY_DELTA:
        return SupplyChangeKind.REDUCTION
    if delta < 0:
        return SupplyChangeKind.BURN
    return SupplyChangeKind.MINT
