"""Selective re-analysis planner (M10.3)."""

from __future__ import annotations

from app.blockchain.continuous.change_detection.models import ChangeDetectionResult
from app.blockchain.continuous.reanalysis.execution_plan import build_execution_plan
from app.blockchain.continuous.reanalysis.impact_analyzer import ImpactAnalyzer
from app.blockchain.continuous.reanalysis.models import ExecutionPlan
from app.blockchain.continuous.reanalysis.module_selector import ModuleSelector


class ReanalysisPlanner:
    """Plan selective analyzer re-execution from change detection results."""

    def __init__(
        self,
        module_selector: ModuleSelector | None = None,
        impact_analyzer: ImpactAnalyzer | None = None,
    ) -> None:
        self._selector = module_selector or ModuleSelector(impact_analyzer)
        self._impact = impact_analyzer or ImpactAnalyzer()

    def plan(self, change_result: ChangeDetectionResult) -> ExecutionPlan:
        if change_result.unchanged:
            return build_execution_plan(
                change_result,
                (),
                selector=self._selector,
                impact=self._impact,
            )
        modules = self._selector.select(change_result.changes)
        return build_execution_plan(
            change_result,
            modules,
            selector=self._selector,
            impact=self._impact,
        )
