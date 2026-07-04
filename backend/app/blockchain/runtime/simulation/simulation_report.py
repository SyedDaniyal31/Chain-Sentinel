"""Simulation result assembly helpers (M9.4)."""

from __future__ import annotations

from app.blockchain.risk.models import RiskEvidence
from app.blockchain.runtime.calltrace.models import RuntimeExecutionReport
from app.blockchain.runtime.simulation.models import (
    SimulatedFinding,
    SimulationResult,
    SimulationScenario,
)
from app.blockchain.runtime.state.models import RuntimeStateReport
from app.models.enums import ConfidenceLevel


def build_simulation_result(
    *,
    scenario: SimulationScenario,
    transaction_hash: str,
    execution_report: RuntimeExecutionReport,
    state_report: RuntimeStateReport,
    evidence: tuple[RiskEvidence, ...],
    findings: tuple[SimulatedFinding, ...],
    confidence: ConfidenceLevel,
) -> SimulationResult:
    """Assemble a complete simulation result from predicted components."""
    return SimulationResult(
        scenario_id=scenario.scenario_id,
        scenario_type=scenario.scenario_type,
        transaction_hash=transaction_hash,
        predicted_execution=execution_report,
        predicted_state=state_report,
        predicted_evidence=evidence,
        predicted_findings=findings,
        assumptions=scenario.assumptions,
        confidence=confidence,
        limitations=scenario.limitations,
    )
