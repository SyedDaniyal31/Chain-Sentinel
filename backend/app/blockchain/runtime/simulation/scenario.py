"""Immutable scenario factories (M9.4)."""

from __future__ import annotations

import hashlib

from app.blockchain.runtime.simulation.models import (
    ScenarioPrecondition,
    ScenarioType,
    SimulatedAction,
    SimulatedActionKind,
    SimulationContext,
    SimulationScenario,
)

MAX_UINT256 = (1 << 256) - 1
PAUSE_SLOT = "0x0000000000000000000000000000000000000000000000000000000000000003"
TIMELOCK_SLOT = "0x0000000000000000000000000000000000000000000000000000000000000002"
DEFAULT_ASSUMPTIONS = (
    "Simulation composes M9.2/M9.3 predictors; EVM is not emulated.",
    "Predicted traces and state diffs are scenario templates, not live chain data.",
)
DEFAULT_LIMITATIONS = (
    "Gas, revert conditions, and reentrancy are not fully modeled.",
    "Cross-contract side effects outside the scenario template are excluded.",
)


def simulation_transaction_hash(scenario_id: str) -> str:
    """Derive a deterministic pseudo transaction hash for a scenario."""
    digest = hashlib.sha256(scenario_id.encode("utf-8")).hexdigest()
    return "0x" + digest


def _scenario_id(scenario_type: ScenarioType, context: SimulationContext) -> str:
    parts = (
        scenario_type.value,
        str(context.chain_id),
        context.contract_address.lower(),
        context.actor_address.lower(),
    )
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:16]
    return f"{scenario_type.value}:{digest}"


def proxy_upgrade_scenario(context: SimulationContext) -> SimulationScenario:
    """Simulate a proxy implementation upgrade."""
    scenario_id = _scenario_id(ScenarioType.PROXY_UPGRADE, context)
    proxy = (context.proxy_address or context.contract_address).lower()
    implementation = (context.implementation_address or context.contract_address).lower()
    new_implementation = (context.new_implementation_address or context.actor_address).lower()
    return SimulationScenario(
        scenario_id=scenario_id,
        scenario_type=ScenarioType.PROXY_UPGRADE,
        context=context,
        preconditions=(
            ScenarioPrecondition("proxy_admin", "Actor holds proxy admin privileges"),
            ScenarioPrecondition("implementation_slot", "Target is an upgradeable proxy"),
        ),
        actions=(
            SimulatedAction(
                kind=SimulatedActionKind.UPGRADE,
                actor=context.actor_address.lower(),
                target=proxy,
                description="upgradeTo(newImplementation)",
                metadata={"new_implementation": new_implementation, "old_implementation": implementation},
            ),
            SimulatedAction(
                kind=SimulatedActionKind.DELEGATECALL,
                actor=proxy,
                target=new_implementation,
                description="Post-upgrade delegated execution",
            ),
        ),
        assumptions=DEFAULT_ASSUMPTIONS,
        limitations=DEFAULT_LIMITATIONS,
        metadata={"proxy": proxy, "implementation": implementation, "new_implementation": new_implementation},
    )


def ownership_transfer_scenario(context: SimulationContext) -> SimulationScenario:
    """Simulate an ownership transfer."""
    scenario_id = _scenario_id(ScenarioType.OWNERSHIP_TRANSFER, context)
    owner = (context.owner_address or context.actor_address).lower()
    new_owner = (context.new_owner_address or context.recipient_address or context.actor_address).lower()
    contract = context.contract_address.lower()
    return SimulationScenario(
        scenario_id=scenario_id,
        scenario_type=ScenarioType.OWNERSHIP_TRANSFER,
        context=context,
        preconditions=(ScenarioPrecondition("current_owner", "Actor is the current owner"),),
        actions=(
            SimulatedAction(
                kind=SimulatedActionKind.CALL,
                actor=owner,
                target=contract,
                description="transferOwnership(newOwner)",
                metadata={"new_owner": new_owner},
            ),
        ),
        assumptions=DEFAULT_ASSUMPTIONS,
        limitations=DEFAULT_LIMITATIONS,
        metadata={"owner": owner, "new_owner": new_owner},
    )


def unlimited_approval_scenario(context: SimulationContext) -> SimulationScenario:
    """Simulate an unlimited ERC20 approval."""
    scenario_id = _scenario_id(ScenarioType.UNLIMITED_APPROVAL, context)
    token = (context.token_address or context.contract_address).lower()
    spender = (context.spender_address or context.recipient_address or context.actor_address).lower()
    owner = context.actor_address.lower()
    return SimulationScenario(
        scenario_id=scenario_id,
        scenario_type=ScenarioType.UNLIMITED_APPROVAL,
        context=context,
        preconditions=(ScenarioPrecondition("token_balance", "Owner holds token balance"),),
        actions=(
            SimulatedAction(
                kind=SimulatedActionKind.APPROVE,
                actor=owner,
                target=token,
                description="approve(spender, type(uint256).max)",
                metadata={"spender": spender, "amount": str(MAX_UINT256)},
            ),
        ),
        assumptions=DEFAULT_ASSUMPTIONS,
        limitations=DEFAULT_LIMITATIONS,
        metadata={"token": token, "owner": owner, "spender": spender},
    )


def unlimited_mint_scenario(context: SimulationContext, *, mint_amount: int = 10**25) -> SimulationScenario:
    """Simulate unlimited token minting."""
    scenario_id = _scenario_id(ScenarioType.UNLIMITED_MINT, context)
    token = (context.token_address or context.contract_address).lower()
    recipient = (context.recipient_address or context.actor_address).lower()
    return SimulationScenario(
        scenario_id=scenario_id,
        scenario_type=ScenarioType.UNLIMITED_MINT,
        context=context,
        preconditions=(ScenarioPrecondition("minter_role", "Actor holds minter or owner role"),),
        actions=(
            SimulatedAction(
                kind=SimulatedActionKind.MINT,
                actor=context.actor_address.lower(),
                target=token,
                description="mint(recipient, largeAmount)",
                metadata={"recipient": recipient, "amount": str(mint_amount)},
            ),
        ),
        assumptions=DEFAULT_ASSUMPTIONS,
        limitations=DEFAULT_LIMITATIONS,
        metadata={"token": token, "recipient": recipient, "mint_amount": mint_amount},
    )


def burn_scenario(context: SimulationContext) -> SimulationScenario:
    """Simulate token burn reducing supply."""
    scenario_id = _scenario_id(ScenarioType.BURN, context)
    token = (context.token_address or context.contract_address).lower()
    burn_amount = 500
    return SimulationScenario(
        scenario_id=scenario_id,
        scenario_type=ScenarioType.BURN,
        context=context,
        preconditions=(ScenarioPrecondition("token_balance", "Actor holds tokens to burn"),),
        actions=(
            SimulatedAction(
                kind=SimulatedActionKind.BURN,
                actor=context.actor_address.lower(),
                target=token,
                description="burn(amount)",
                metadata={"amount": str(burn_amount)},
            ),
        ),
        assumptions=DEFAULT_ASSUMPTIONS,
        limitations=DEFAULT_LIMITATIONS,
        metadata={"token": token, "burn_amount": burn_amount},
    )


def pause_scenario(context: SimulationContext) -> SimulationScenario:
    """Simulate contract pause flag activation."""
    scenario_id = _scenario_id(ScenarioType.PAUSE, context)
    contract = context.contract_address.lower()
    return SimulationScenario(
        scenario_id=scenario_id,
        scenario_type=ScenarioType.PAUSE,
        context=context,
        preconditions=(ScenarioPrecondition("pauser_role", "Actor holds pauser role"),),
        actions=(
            SimulatedAction(
                kind=SimulatedActionKind.STORAGE_WRITE,
                actor=context.actor_address.lower(),
                target=contract,
                description="pause() sets paused storage flag",
                metadata={"slot": PAUSE_SLOT, "after": "0x01"},
            ),
        ),
        assumptions=DEFAULT_ASSUMPTIONS,
        limitations=DEFAULT_LIMITATIONS + ("Pause slot mapping is protocol-specific.",),
        metadata={"slot": PAUSE_SLOT},
    )


def unpause_scenario(context: SimulationContext) -> SimulationScenario:
    """Simulate contract unpause."""
    scenario_id = _scenario_id(ScenarioType.UNPAUSE, context)
    contract = context.contract_address.lower()
    return SimulationScenario(
        scenario_id=scenario_id,
        scenario_type=ScenarioType.UNPAUSE,
        context=context,
        preconditions=(ScenarioPrecondition("pauser_role", "Actor holds pauser role"),),
        actions=(
            SimulatedAction(
                kind=SimulatedActionKind.STORAGE_WRITE,
                actor=context.actor_address.lower(),
                target=contract,
                description="unpause() clears paused storage flag",
                metadata={"slot": PAUSE_SLOT, "after": "0x00"},
            ),
        ),
        assumptions=DEFAULT_ASSUMPTIONS,
        limitations=DEFAULT_LIMITATIONS + ("Pause slot mapping is protocol-specific.",),
        metadata={"slot": PAUSE_SLOT},
    )


def timelock_reduction_scenario(context: SimulationContext) -> SimulationScenario:
    """Simulate timelock delay reduction."""
    scenario_id = _scenario_id(ScenarioType.TIMELOCK_REDUCTION, context)
    contract = (context.timelock_address or context.contract_address).lower()
    new_delay = 0
    return SimulationScenario(
        scenario_id=scenario_id,
        scenario_type=ScenarioType.TIMELOCK_REDUCTION,
        context=context,
        preconditions=(ScenarioPrecondition("timelock_admin", "Actor controls timelock admin"),),
        actions=(
            SimulatedAction(
                kind=SimulatedActionKind.STORAGE_WRITE,
                actor=context.actor_address.lower(),
                target=contract,
                description="updateDelay(0)",
                metadata={"slot": TIMELOCK_SLOT, "after": "0x" + format(new_delay, "064x")},
            ),
        ),
        assumptions=DEFAULT_ASSUMPTIONS,
        limitations=DEFAULT_LIMITATIONS + ("Timelock storage layout varies by implementation.",),
        metadata={"slot": TIMELOCK_SLOT, "new_delay": new_delay},
    )


def governance_proposal_execution_scenario(context: SimulationContext) -> SimulationScenario:
    """Simulate governance proposal execution."""
    scenario_id = _scenario_id(ScenarioType.GOVERNANCE_PROPOSAL_EXECUTION, context)
    governor = (context.governor_address or context.contract_address).lower()
    target = (context.recipient_address or context.contract_address).lower()
    return SimulationScenario(
        scenario_id=scenario_id,
        scenario_type=ScenarioType.GOVERNANCE_PROPOSAL_EXECUTION,
        context=context,
        preconditions=(
            ScenarioPrecondition("proposal_passed", "Governance proposal has passed quorum"),
            ScenarioPrecondition("timelock_elapsed", "Timelock delay has elapsed"),
        ),
        actions=(
            SimulatedAction(
                kind=SimulatedActionKind.GOVERNANCE_EXECUTE,
                actor=context.actor_address.lower(),
                target=governor,
                description="execute(proposalId, targets, values, calldatas)",
                metadata={"execution_target": target},
            ),
            SimulatedAction(
                kind=SimulatedActionKind.CALL,
                actor=governor,
                target=target,
                description="Execute proposal payload",
            ),
        ),
        assumptions=DEFAULT_ASSUMPTIONS,
        limitations=DEFAULT_LIMITATIONS + ("Proposal calldata is not decoded in simulation.",),
        metadata={"governor": governor, "target": target},
    )


SCENARIO_FACTORIES: dict[ScenarioType, object] = {
    ScenarioType.PROXY_UPGRADE: proxy_upgrade_scenario,
    ScenarioType.OWNERSHIP_TRANSFER: ownership_transfer_scenario,
    ScenarioType.UNLIMITED_APPROVAL: unlimited_approval_scenario,
    ScenarioType.UNLIMITED_MINT: unlimited_mint_scenario,
    ScenarioType.BURN: burn_scenario,
    ScenarioType.PAUSE: pause_scenario,
    ScenarioType.UNPAUSE: unpause_scenario,
    ScenarioType.TIMELOCK_REDUCTION: timelock_reduction_scenario,
    ScenarioType.GOVERNANCE_PROPOSAL_EXECUTION: governance_proposal_execution_scenario,
}
