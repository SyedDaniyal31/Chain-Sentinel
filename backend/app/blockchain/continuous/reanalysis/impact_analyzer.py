"""Map change types to affected intelligence modules (M10.3)."""

from __future__ import annotations

from app.blockchain.continuous.change_detection.models import ChangeEvent, ChangeType
from app.blockchain.continuous.reanalysis.models import ReanalysisModule

CHANGE_TYPE_MODULES: dict[ChangeType, tuple[ReanalysisModule, ...]] = {
    ChangeType.IMPLEMENTATION_CHANGED: (
        ReanalysisModule.CAPABILITY,
        ReanalysisModule.PROTOCOL,
        ReanalysisModule.THREAT,
    ),
    ChangeType.OWNER_CHANGED: (
        ReanalysisModule.GOVERNANCE,
        ReanalysisModule.THREAT,
    ),
    ChangeType.PROXY_ADMIN_CHANGED: (
        ReanalysisModule.GOVERNANCE,
        ReanalysisModule.THREAT,
    ),
    ChangeType.GOVERNANCE_CHANGED: (
        ReanalysisModule.GOVERNANCE,
        ReanalysisModule.THREAT,
    ),
    ChangeType.LIQUIDITY_CHANGED: (ReanalysisModule.LIQUIDITY,),
    ChangeType.TREASURY_CHANGED: (
        ReanalysisModule.GOVERNANCE,
        ReanalysisModule.THREAT,
    ),
    ChangeType.BYTECODE_CHANGED: (
        ReanalysisModule.CAPABILITY,
        ReanalysisModule.PROTOCOL,
        ReanalysisModule.THREAT,
    ),
    ChangeType.DEPENDENCY_CHANGED: (
        ReanalysisModule.PROTOCOL,
        ReanalysisModule.RELATIONSHIP,
    ),
    ChangeType.RUNTIME_FINGERPRINT_CHANGED: (
        ReanalysisModule.PROTOCOL,
        ReanalysisModule.THREAT,
    ),
}


class ImpactAnalyzer:
    """Determine intelligence modules impacted by detected protocol changes."""

    def modules_for_change(self, change_type: ChangeType) -> tuple[ReanalysisModule, ...]:
        return CHANGE_TYPE_MODULES.get(change_type, ())

    def modules_for_event(self, event: ChangeEvent) -> tuple[ReanalysisModule, ...]:
        return self.modules_for_change(event.change_type)

    def affected_contracts(self, events: tuple[ChangeEvent, ...]) -> tuple[str, ...]:
        addresses: set[str] = set()
        for event in events:
            addresses.update(event.affected_contracts)
        return tuple(sorted(addresses))
