"""Unit tests for selective re-analysis engine (M10.3)."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.blockchain.continuous.change_detection.models import (
    ChangeDetectionResult,
    ChangeEvent,
    ChangeSeverity,
    ChangeType,
)
from app.blockchain.continuous.reanalysis import (
    CallableModuleExecutor,
    DeltaBuilder,
    ImpactAnalyzer,
    ReanalysisModule,
    ReanalysisOrchestrator,
    ReanalysisPlanner,
)
from app.blockchain.continuous.protocol_subscription import watch_id
from app.blockchain.risk.evidence import create_evidence
from app.blockchain.risk.evidence_types import EvidenceCategory, EvidenceSeverity, EvidenceSource
from app.models.enums import ConfidenceLevel

ROOT = "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
PROXY = "0xcccccccccccccccccccccccccccccccccccccccc"
WATCH = watch_id(1, ROOT)
NOW = datetime(2026, 6, 13, 14, 0, tzinfo=timezone.utc)


def _change(
    change_type: ChangeType,
    *,
    before: str | None = "before",
    after: str | None = "after",
) -> ChangeEvent:
    return ChangeEvent(
        event_id=f"{WATCH}:{change_type.value}:test",
        change_type=change_type,
        severity=ChangeSeverity.HIGH,
        before=before,
        after=after,
        affected_contracts=(PROXY,),
        timestamp=NOW,
        confidence=ConfidenceLevel.HIGH,
    )


def _result(*changes: ChangeEvent) -> ChangeDetectionResult:
    return ChangeDetectionResult(
        watch_id=WATCH,
        baseline_snapshot_id=f"{WATCH}:baseline",
        current_snapshot_id=f"{WATCH}:current",
        detected_at=NOW,
        changes=changes,
        unchanged=len(changes) == 0,
    )


def _evidence(signal: str, *, score: str = "10.00") -> object:
    return create_evidence(
        source=EvidenceSource.GOVERNANCE,
        category=EvidenceCategory.AUTHORITY,
        signal=signal,
        severity=EvidenceSeverity.MEDIUM,
        score=Decimal(score),
        confidence=ConfidenceLevel.HIGH,
        reason=f"reason:{signal}",
        metadata={"signal": signal},
    )


@pytest.mark.parametrize(
    ("change_type", "expected_modules"),
    [
        (
            ChangeType.IMPLEMENTATION_CHANGED,
            (
                ReanalysisModule.CAPABILITY,
                ReanalysisModule.PROTOCOL,
                ReanalysisModule.THREAT,
            ),
        ),
        (
            ChangeType.OWNER_CHANGED,
            (ReanalysisModule.GOVERNANCE, ReanalysisModule.THREAT),
        ),
        (ChangeType.LIQUIDITY_CHANGED, (ReanalysisModule.LIQUIDITY,)),
        (
            ChangeType.DEPENDENCY_CHANGED,
            (ReanalysisModule.PROTOCOL, ReanalysisModule.RELATIONSHIP),
        ),
        (
            ChangeType.BYTECODE_CHANGED,
            (
                ReanalysisModule.CAPABILITY,
                ReanalysisModule.PROTOCOL,
                ReanalysisModule.THREAT,
            ),
        ),
    ],
)
def test_execution_plan_modules(change_type: ChangeType, expected_modules: tuple[ReanalysisModule, ...]) -> None:
    plan = ReanalysisPlanner().plan(_result(_change(change_type)))

    assert plan.modules == expected_modules
    assert change_type in plan.triggered_by
    assert plan.affected_contracts == (PROXY,)


def test_unchanged_detection_produces_empty_plan() -> None:
    plan = ReanalysisPlanner().plan(_result())

    assert plan.modules == ()
    assert plan.triggered_by == ()


def test_deterministic_module_ordering() -> None:
    result = _result(
        _change(ChangeType.IMPLEMENTATION_CHANGED),
        _change(ChangeType.LIQUIDITY_CHANGED),
        _change(ChangeType.DEPENDENCY_CHANGED),
    )

    plan_one = ReanalysisPlanner().plan(result)
    plan_two = ReanalysisPlanner().plan(result)

    assert plan_one.modules == plan_two.modules
    assert plan_one.plan_id == plan_two.plan_id
    assert plan_one.modules == (
        ReanalysisModule.CAPABILITY,
        ReanalysisModule.LIQUIDITY,
        ReanalysisModule.PROTOCOL,
        ReanalysisModule.RELATIONSHIP,
        ReanalysisModule.THREAT,
    )


def test_impact_analyzer_maps_implementation_change() -> None:
    modules = ImpactAnalyzer().modules_for_change(ChangeType.IMPLEMENTATION_CHANGED)

    assert ReanalysisModule.CAPABILITY in modules
    assert ReanalysisModule.PROTOCOL in modules
    assert ReanalysisModule.THREAT in modules


@pytest.mark.asyncio
async def test_orchestrator_executes_selected_modules_only() -> None:
    executed: list[ReanalysisModule] = []

    def _handler(module: ReanalysisModule):
        def inner(_context: object) -> list:
            executed.append(module)
            return [_evidence(module.value)]

        return inner

    executor = CallableModuleExecutor(
        {
            ReanalysisModule.CAPABILITY: _handler(ReanalysisModule.CAPABILITY),
            ReanalysisModule.PROTOCOL: _handler(ReanalysisModule.PROTOCOL),
            ReanalysisModule.THREAT: _handler(ReanalysisModule.THREAT),
            ReanalysisModule.GOVERNANCE: _handler(ReanalysisModule.GOVERNANCE),
            ReanalysisModule.LIQUIDITY: _handler(ReanalysisModule.LIQUIDITY),
            ReanalysisModule.RELATIONSHIP: _handler(ReanalysisModule.RELATIONSHIP),
        }
    )
    orchestrator = ReanalysisOrchestrator(executor=executor)
    result = await orchestrator.run(
        _result(_change(ChangeType.OWNER_CHANGED)),
        previous_evidence=(),
        root_address=ROOT,
    )

    assert result.executed_modules == (ReanalysisModule.GOVERNANCE, ReanalysisModule.THREAT)
    assert executed == [ReanalysisModule.GOVERNANCE, ReanalysisModule.THREAT]
    assert len(result.new_evidence) == 2


@pytest.mark.asyncio
async def test_delta_generation() -> None:
    previous = (_evidence("stable", score="10.00"), _evidence("removed", score="5.00"))
    updated_before = _evidence("updated", score="10.00")
    updated_after = _evidence("updated", score="25.00")

    executor = CallableModuleExecutor(
        {
            ReanalysisModule.LIQUIDITY: lambda _ctx: [
                _evidence("stable", score="10.00"),
                updated_after,
                _evidence("added", score="15.00"),
            ],
        }
    )
    orchestrator = ReanalysisOrchestrator(executor=executor)
    result = await orchestrator.run(
        _result(_change(ChangeType.LIQUIDITY_CHANGED)),
        previous_evidence=(previous[0], previous[1], updated_before),
        root_address=ROOT,
    )

    delta = result.evidence_delta
    added_signals = {item.metadata.get("signal") for item in delta.added}
    removed_signals = {item.metadata.get("signal") for item in delta.removed}
    assert "added" in added_signals
    assert "removed" in removed_signals
    assert len(delta.updated) == 1
    assert delta.updated[0][0].score == Decimal("10.00")
    assert delta.updated[0][1].score == Decimal("25.00")
    assert result.metrics.evidence_added_count == len(delta.added)
    assert result.metrics.evidence_removed_count == len(delta.removed)
    assert result.metrics.evidence_updated_count == 1


def test_delta_builder_directly() -> None:
    previous = (_evidence("alpha"),)
    current = (_evidence("alpha", score="20.00"), _evidence("beta"))

    delta = DeltaBuilder().build(previous, current)

    assert len(delta.added) == 1
    assert delta.added[0].metadata["signal"] == "beta"
    assert len(delta.updated) == 1
    assert len(delta.removed) == 0
