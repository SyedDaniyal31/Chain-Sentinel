"""Selective re-analysis orchestrator (M10.3)."""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any

from app.blockchain.continuous.change_detection.models import ChangeDetectionResult
from app.blockchain.continuous.reanalysis.delta_builder import DeltaBuilder
from app.blockchain.continuous.reanalysis.models import (
    EvidenceDelta,
    ExecutionPlan,
    ReanalysisMetrics,
    ReanalysisModule,
    ReanalysisResult,
)
from app.blockchain.continuous.reanalysis.planner import ReanalysisPlanner
from app.blockchain.risk.evidence import merge_evidence
from app.blockchain.risk.evidence_builder import RiskEvidenceBuilder, RiskEvidenceBundle
from app.blockchain.risk.models import RiskEvidence


@dataclass(frozen=True, slots=True)
class ReanalysisExecutionContext:
    """Runtime context for selective module execution."""

    watch_id: str
    chain_id: int
    root_address: str
    affected_contracts: tuple[str, ...]
    change_result: ChangeDetectionResult
    bundles: Mapping[ReanalysisModule, RiskEvidenceBundle] = field(default_factory=dict)


class ModuleExecutor(ABC):
    """Execute a single intelligence module and return normalized evidence."""

    @abstractmethod
    async def execute(
        self,
        module: ReanalysisModule,
        context: ReanalysisExecutionContext,
    ) -> list[RiskEvidence]:
        """Run one analyzer module without performing a full rescan."""


class RiskEvidenceBuilderExecutor(ModuleExecutor):
    """Reuse RiskEvidenceBuilder to translate partial analyzer outputs into evidence."""

    def __init__(self, builder: RiskEvidenceBuilder | None = None) -> None:
        self._builder = builder or RiskEvidenceBuilder()

    async def execute(
        self,
        module: ReanalysisModule,
        context: ReanalysisExecutionContext,
    ) -> list[RiskEvidence]:
        bundle = context.bundles.get(module)
        if bundle is None:
            return []
        return _evidence_for_module(self._builder, module, bundle)


class CallableModuleExecutor(ModuleExecutor):
    """Inject module-specific evidence producers for tests or custom wiring."""

    def __init__(
        self,
        handlers: Mapping[ReanalysisModule, Callable[[ReanalysisExecutionContext], list[RiskEvidence]]],
    ) -> None:
        self._handlers = dict(handlers)

    async def execute(
        self,
        module: ReanalysisModule,
        context: ReanalysisExecutionContext,
    ) -> list[RiskEvidence]:
        handler = self._handlers.get(module)
        if handler is None:
            return []
        return list(handler(context))


class ReanalysisOrchestrator:
    """Plan and execute selective analyzer re-runs driven by change detection."""

    def __init__(
        self,
        planner: ReanalysisPlanner | None = None,
        executor: ModuleExecutor | None = None,
        delta_builder: DeltaBuilder | None = None,
    ) -> None:
        self._planner = planner or ReanalysisPlanner()
        self._executor = executor or RiskEvidenceBuilderExecutor()
        self._delta_builder = delta_builder or DeltaBuilder()

    async def run(
        self,
        change_result: ChangeDetectionResult,
        *,
        previous_evidence: tuple[RiskEvidence, ...] = (),
        chain_id: int = 1,
        root_address: str | None = None,
        bundles: Mapping[ReanalysisModule, RiskEvidenceBundle] | None = None,
    ) -> ReanalysisResult:
        started = time.perf_counter()
        plan = self._planner.plan(change_result)
        context = ReanalysisExecutionContext(
            watch_id=change_result.watch_id,
            chain_id=chain_id,
            root_address=(root_address or change_result.watch_id.split(":", 1)[-1]).lower(),
            affected_contracts=plan.affected_contracts,
            change_result=change_result,
            bundles=bundles or {},
        )

        executed: list[ReanalysisModule] = []
        evidence_groups: list[list[RiskEvidence]] = []
        for module in plan.modules:
            module_evidence = await self._executor.execute(module, context)
            executed.append(module)
            evidence_groups.append(module_evidence)

        new_evidence = tuple(merge_evidence(*evidence_groups))
        evidence_delta = self._delta_builder.build(previous_evidence, new_evidence)
        duration_ms = (time.perf_counter() - started) * 1000

        return ReanalysisResult(
            watch_id=change_result.watch_id,
            execution_plan=plan,
            executed_modules=tuple(executed),
            new_evidence=new_evidence,
            evidence_delta=evidence_delta,
            metrics=_build_metrics(plan, executed, evidence_delta, duration_ms),
            change_result=change_result,
        )


def _evidence_for_module(
    builder: RiskEvidenceBuilder,
    module: ReanalysisModule,
    bundle: RiskEvidenceBundle,
) -> list[RiskEvidence]:
    if module == ReanalysisModule.GOVERNANCE and bundle.governance is not None:
        return builder.from_governance_analysis(bundle.governance)
    if module == ReanalysisModule.LIQUIDITY and bundle.liquidity is not None:
        return builder.from_liquidity_analysis(bundle.liquidity)
    if module == ReanalysisModule.PROTOCOL and bundle.protocol is not None:
        return builder.from_protocol_intelligence(bundle.protocol)
    if module == ReanalysisModule.RELATIONSHIP and bundle.protocol is not None:
        return builder.from_protocol_relationship_analysis(bundle.protocol.relationships)
    if module == ReanalysisModule.THREAT:
        if bundle.protocol is not None and bundle.protocol.threat_surface is not None:
            return builder.from_threat_surface_analysis(bundle.protocol.threat_surface)
        if bundle.threat_surface is not None:
            return builder.from_threat_surface_analysis(bundle.threat_surface)
    if module == ReanalysisModule.CAPABILITY and bundle.contract_input is not None:
        return builder.from_contract_risk_input(bundle.contract_input)
    return []


def _build_metrics(
    plan: ExecutionPlan,
    executed: list[ReanalysisModule],
    delta: EvidenceDelta,
    duration_ms: float,
) -> ReanalysisMetrics:
    return ReanalysisMetrics(
        modules_planned=len(plan.modules),
        modules_executed=len(executed),
        duration_ms=duration_ms,
        evidence_added_count=len(delta.added),
        evidence_removed_count=len(delta.removed),
        evidence_updated_count=len(delta.updated),
    )
