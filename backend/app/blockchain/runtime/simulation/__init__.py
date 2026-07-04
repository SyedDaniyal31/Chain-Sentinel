"""Exploit simulation intelligence (M9.4)."""

from app.blockchain.runtime.simulation.attack_executor import AttackExecutor
from app.blockchain.runtime.simulation.attack_library import (
    ALL_ATTACKS,
    ATTACK_LIBRARY,
    BRIDGE_COMPROMISE,
    GOVERNANCE_CAPTURE,
    ORACLE_MANIPULATION,
    PRIVILEGE_ESCALATION,
    TREASURY_DRAIN,
    UNLIMITED_APPROVAL_ATTACK,
    UNLIMITED_MINT_ATTACK,
    UPGRADE_ATTACK,
)
from app.blockchain.runtime.simulation.evidence_mapper import build_simulated_findings, map_simulation_evidence
from app.blockchain.runtime.simulation.execution_predictor import ExecutionPredictor
from app.blockchain.runtime.simulation.models import (
    AttackScenario,
    AttackType,
    ExpectedOutcome,
    ScenarioPrecondition,
    ScenarioType,
    SimulatedAction,
    SimulatedActionKind,
    SimulatedFinding,
    SimulationContext,
    SimulationResult,
    SimulationScenario,
)
from app.blockchain.runtime.simulation.scenario import (
    SCENARIO_FACTORIES,
    burn_scenario,
    governance_proposal_execution_scenario,
    ownership_transfer_scenario,
    pause_scenario,
    proxy_upgrade_scenario,
    simulation_transaction_hash,
    timelock_reduction_scenario,
    unlimited_approval_scenario,
    unlimited_mint_scenario,
    unpause_scenario,
)
from app.blockchain.runtime.simulation.scenario_builder import ScenarioBuilder, ScenarioValidationError
from app.blockchain.runtime.simulation.simulation_engine import SimulationEngine, build_scenario
from app.blockchain.runtime.simulation.simulation_report import build_simulation_result
from app.blockchain.runtime.simulation.state_predictor import StatePredictor

__all__ = [
    "ALL_ATTACKS",
    "ATTACK_LIBRARY",
    "AttackExecutor",
    "AttackScenario",
    "AttackType",
    "BRIDGE_COMPROMISE",
    "ExpectedOutcome",
    "ExecutionPredictor",
    "GOVERNANCE_CAPTURE",
    "ORACLE_MANIPULATION",
    "PRIVILEGE_ESCALATION",
    "SCENARIO_FACTORIES",
    "ScenarioBuilder",
    "ScenarioPrecondition",
    "ScenarioType",
    "ScenarioValidationError",
    "SimulatedAction",
    "SimulatedActionKind",
    "SimulatedFinding",
    "SimulationContext",
    "SimulationEngine",
    "SimulationResult",
    "SimulationScenario",
    "StatePredictor",
    "TREASURY_DRAIN",
    "UNLIMITED_APPROVAL_ATTACK",
    "UNLIMITED_MINT_ATTACK",
    "UPGRADE_ATTACK",
    "build_scenario",
    "build_simulated_findings",
    "build_simulation_result",
    "burn_scenario",
    "governance_proposal_execution_scenario",
    "map_simulation_evidence",
    "ownership_transfer_scenario",
    "pause_scenario",
    "proxy_upgrade_scenario",
    "simulation_transaction_hash",
    "timelock_reduction_scenario",
    "unlimited_approval_scenario",
    "unlimited_mint_scenario",
    "unpause_scenario",
]
