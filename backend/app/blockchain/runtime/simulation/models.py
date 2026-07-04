"""Exploit simulation domain models (M9.4)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from app.blockchain.risk.models import RiskEvidence
from app.blockchain.runtime.calltrace.models import RuntimeExecutionReport
from app.blockchain.runtime.state.models import RuntimeStateReport
from app.models.enums import ConfidenceLevel


class ScenarioType(StrEnum):
    """Deterministic exploit simulation scenario types."""

    PROXY_UPGRADE = "proxy_upgrade"
    OWNERSHIP_TRANSFER = "ownership_transfer"
    UNLIMITED_APPROVAL = "unlimited_approval"
    UNLIMITED_MINT = "unlimited_mint"
    BURN = "burn"
    PAUSE = "pause"
    UNPAUSE = "unpause"
    TIMELOCK_REDUCTION = "timelock_reduction"
    GOVERNANCE_PROPOSAL_EXECUTION = "governance_proposal_execution"


class AttackType(StrEnum):
    """Reusable attack scenario classifications."""

    UPGRADE_ATTACK = "upgrade_attack"
    GOVERNANCE_CAPTURE = "governance_capture"
    TREASURY_DRAIN = "treasury_drain"
    UNLIMITED_MINT = "unlimited_mint"
    UNLIMITED_APPROVAL = "unlimited_approval"
    ORACLE_MANIPULATION = "oracle_manipulation"
    BRIDGE_COMPROMISE = "bridge_compromise"
    PRIVILEGE_ESCALATION = "privilege_escalation"


class SimulatedActionKind(StrEnum):
    """High-level simulated execution action."""

    CALL = "call"
    DELEGATECALL = "delegatecall"
    APPROVE = "approve"
    TRANSFER = "transfer"
    MINT = "mint"
    BURN = "burn"
    UPGRADE = "upgrade"
    GOVERNANCE_EXECUTE = "governance_execute"
    STORAGE_WRITE = "storage_write"


@dataclass(frozen=True, slots=True)
class ScenarioPrecondition:
    """Required condition for a scenario to be simulatable."""

    key: str
    description: str
    required: bool = True
    satisfied: bool = True


@dataclass(frozen=True, slots=True)
class SimulatedAction:
    """Single simulated action within a scenario."""

    kind: SimulatedActionKind
    actor: str
    target: str | None
    description: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class SimulationContext:
    """Addresses and chain context for a simulation."""

    chain_id: int
    actor_address: str
    contract_address: str
    proxy_address: str | None = None
    implementation_address: str | None = None
    new_implementation_address: str | None = None
    token_address: str | None = None
    owner_address: str | None = None
    new_owner_address: str | None = None
    spender_address: str | None = None
    recipient_address: str | None = None
    governor_address: str | None = None
    treasury_address: str | None = None
    timelock_address: str | None = None
    bridge_address: str | None = None
    oracle_address: str | None = None


@dataclass(frozen=True, slots=True)
class SimulationScenario:
    """Immutable deterministic simulation scenario."""

    scenario_id: str
    scenario_type: ScenarioType
    context: SimulationContext
    preconditions: tuple[ScenarioPrecondition, ...]
    actions: tuple[SimulatedAction, ...]
    assumptions: tuple[str, ...]
    limitations: tuple[str, ...]
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ExpectedOutcome:
    """Predicted outcome descriptor for attack library entries."""

    signal: str
    description: str
    severity: str | None = None


@dataclass(frozen=True, slots=True)
class AttackScenario:
    """Reusable attack definition composed of one or more simulation scenarios."""

    attack_id: str
    attack_type: AttackType
    name: str
    description: str
    preconditions: tuple[ScenarioPrecondition, ...]
    actions: tuple[SimulatedAction, ...]
    scenarios: tuple[SimulationScenario, ...]
    expected_state_changes: tuple[str, ...]
    expected_evidence: tuple[ExpectedOutcome, ...]
    limitations: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SimulatedFinding:
    """High-level predicted security finding from simulation."""

    finding_id: str
    scenario_type: ScenarioType
    signal: str
    description: str
    severity: str


@dataclass(frozen=True, slots=True)
class SimulationResult:
    """Complete output of an exploit simulation run."""

    scenario_id: str
    scenario_type: ScenarioType
    transaction_hash: str
    predicted_execution: RuntimeExecutionReport
    predicted_state: RuntimeStateReport
    predicted_evidence: tuple[RiskEvidence, ...]
    predicted_findings: tuple[SimulatedFinding, ...]
    assumptions: tuple[str, ...]
    confidence: ConfidenceLevel
    limitations: tuple[str, ...]
