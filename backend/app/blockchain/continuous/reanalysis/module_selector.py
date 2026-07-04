"""Selective module selection utilities (M10.3)."""

from __future__ import annotations

from app.blockchain.continuous.change_detection.models import ChangeEvent, ChangeType
from app.blockchain.continuous.reanalysis.impact_analyzer import ImpactAnalyzer
from app.blockchain.continuous.reanalysis.models import ReanalysisModule

MODULE_ORDER: tuple[ReanalysisModule, ...] = (
    ReanalysisModule.CAPABILITY,
    ReanalysisModule.GOVERNANCE,
    ReanalysisModule.LIQUIDITY,
    ReanalysisModule.PROTOCOL,
    ReanalysisModule.RELATIONSHIP,
    ReanalysisModule.THREAT,
)


class ModuleSelector:
    """Select a deterministic set of modules to re-execute."""

    def __init__(self, impact_analyzer: ImpactAnalyzer | None = None) -> None:
        self._impact = impact_analyzer or ImpactAnalyzer()

    def select(self, events: tuple[ChangeEvent, ...]) -> tuple[ReanalysisModule, ...]:
        selected: set[ReanalysisModule] = set()
        for event in events:
            selected.update(self._impact.modules_for_event(event))
        return tuple(module for module in MODULE_ORDER if module in selected)

    def triggered_change_types(self, events: tuple[ChangeEvent, ...]) -> tuple[ChangeType, ...]:
        return tuple(sorted({event.change_type for event in events}, key=lambda item: item.value))
