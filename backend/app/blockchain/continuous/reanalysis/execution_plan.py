"""Execution plan construction (M10.3)."""

from __future__ import annotations

import hashlib

from app.blockchain.continuous.change_detection.models import ChangeDetectionResult
from app.blockchain.continuous.reanalysis.impact_analyzer import ImpactAnalyzer
from app.blockchain.continuous.reanalysis.models import ExecutionPlan, ReanalysisModule
from app.blockchain.continuous.reanalysis.module_selector import ModuleSelector


def build_execution_plan(
    change_result: ChangeDetectionResult,
    modules: tuple[ReanalysisModule, ...],
    *,
    selector: ModuleSelector | None = None,
    impact: ImpactAnalyzer | None = None,
) -> ExecutionPlan:
    """Build a deterministic execution plan from change detection output."""
    module_selector = selector or ModuleSelector(impact)
    triggered_by = module_selector.triggered_change_types(change_result.changes)
    impact_analyzer = impact or ImpactAnalyzer()
    affected = impact_analyzer.affected_contracts(change_result.changes)
    plan_id = _plan_id(change_result.watch_id, modules, triggered_by)
    return ExecutionPlan(
        plan_id=plan_id,
        watch_id=change_result.watch_id,
        modules=modules,
        triggered_by=triggered_by,
        affected_contracts=affected,
        metadata={
            "baseline_snapshot_id": change_result.baseline_snapshot_id,
            "current_snapshot_id": change_result.current_snapshot_id,
        },
    )


def _plan_id(
    watch_id: str,
    modules: tuple[ReanalysisModule, ...],
    triggered_by: tuple[object, ...],
) -> str:
    payload = "|".join(
        [
            watch_id,
            ",".join(module.value for module in modules),
            ",".join(item.value for item in triggered_by),
        ]
    )
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
    return f"{watch_id}:plan:{digest}"
