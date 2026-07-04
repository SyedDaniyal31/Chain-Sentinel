"""Exploit simulation orchestrator (M9.4)."""

from __future__ import annotations

from app.blockchain.runtime.simulation.evidence_mapper import build_simulated_findings, map_simulation_evidence
from app.blockchain.runtime.simulation.execution_predictor import ExecutionPredictor
from app.blockchain.runtime.simulation.models import (
    AttackScenario,
    ScenarioType,
    SimulationContext,
    SimulationResult,
    SimulationScenario,
)
from app.blockchain.runtime.simulation.scenario import simulation_transaction_hash
from app.blockchain.runtime.simulation.scenario_builder import ScenarioBuilder
from app.blockchain.runtime.simulation.simulation_report import build_simulation_result
from app.blockchain.runtime.simulation.state_predictor import StatePredictor
from app.models.enums import ConfidenceLevel

SCENARIO_CONFIDENCE: dict[ScenarioType, ConfidenceLevel] = {
    ScenarioType.PROXY_UPGRADE: ConfidenceLevel.HIGH,
    ScenarioType.OWNERSHIP_TRANSFER: ConfidenceLevel.HIGH,
    ScenarioType.UNLIMITED_APPROVAL: ConfidenceLevel.HIGH,
    ScenarioType.UNLIMITED_MINT: ConfidenceLevel.HIGH,
    ScenarioType.BURN: ConfidenceLevel.MEDIUM,
    ScenarioType.PAUSE: ConfidenceLevel.MEDIUM,
    ScenarioType.UNPAUSE: ConfidenceLevel.MEDIUM,
    ScenarioType.TIMELOCK_REDUCTION: ConfidenceLevel.MEDIUM,
    ScenarioType.GOVERNANCE_PROPOSAL_EXECUTION: ConfidenceLevel.MEDIUM,
}


class SimulationEngine:
    """Deterministic exploit simulation framework composing M9.2 and M9.3 predictors."""

    def __init__(
        self,
        execution_predictor: ExecutionPredictor | None = None,
        state_predictor: StatePredictor | None = None,
        scenario_builder: ScenarioBuilder | None = None,
    ) -> None:
        self._execution_predictor = execution_predictor or ExecutionPredictor()
        self._state_predictor = state_predictor or StatePredictor()
        self._scenario_builder = scenario_builder or ScenarioBuilder()

    async def simulate(self, scenario: SimulationScenario) -> SimulationResult:
        self._scenario_builder.validate(scenario.scenario_type, scenario.context)
        execution_report = await self._execution_predictor.predict(scenario)
        state_report = await self._state_predictor.predict(
            scenario,
            execution_report=execution_report,
        )
        evidence = map_simulation_evidence(
            scenario=scenario,
            execution_report=execution_report,
            state_report=state_report,
        )
        findings = build_simulated_findings(scenario=scenario, evidence=evidence)
        confidence = SCENARIO_CONFIDENCE.get(scenario.scenario_type, ConfidenceLevel.MEDIUM)
        return build_simulation_result(
            scenario=scenario,
            transaction_hash=simulation_transaction_hash(scenario.scenario_id),
            execution_report=execution_report,
            state_report=state_report,
            evidence=evidence,
            findings=findings,
            confidence=confidence,
        )

    async def simulate_type(
        self,
        scenario_type: ScenarioType,
        context: SimulationContext,
    ) -> SimulationResult:
        scenario = self._scenario_builder.build(scenario_type, context)
        return await self.simulate(scenario)

    async def simulate_attack(self, attack: AttackScenario) -> tuple[SimulationResult, ...]:
        results: list[SimulationResult] = []
        for scenario in attack.scenarios:
            results.append(await self.simulate(scenario))
        return tuple(results)


def build_scenario(scenario_type: ScenarioType, context: SimulationContext) -> SimulationScenario:
    """Build a validated scenario using the shared factory registry."""
    builder = ScenarioBuilder()
    return builder.build(scenario_type, context)
