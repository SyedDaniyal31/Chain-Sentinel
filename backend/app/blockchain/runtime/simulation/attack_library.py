"""Reusable attack scenario library (M9.4)."""

from __future__ import annotations

from app.blockchain.runtime.simulation.models import (
    AttackScenario,
    AttackType,
    ExpectedOutcome,
    ScenarioPrecondition,
    SimulatedAction,
    SimulatedActionKind,
    SimulationContext,
)
from app.blockchain.runtime.simulation.scenario import (
    governance_proposal_execution_scenario,
    ownership_transfer_scenario,
    proxy_upgrade_scenario,
    timelock_reduction_scenario,
    unlimited_approval_scenario,
    unlimited_mint_scenario,
)


def _base_context(**overrides: object) -> SimulationContext:
    actor = "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    contract = "0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
    payload = {
        "chain_id": 1,
        "actor_address": actor,
        "contract_address": contract,
    }
    payload.update(overrides)
    return SimulationContext(**payload)


UPGRADE_ATTACK = AttackScenario(
    attack_id="attack:upgrade",
    attack_type=AttackType.UPGRADE_ATTACK,
    name="Proxy Upgrade Attack",
    description="Malicious actor upgrades proxy implementation to attacker-controlled logic.",
    preconditions=(
        ScenarioPrecondition("compromised_admin", "Attacker controls proxy admin key"),
    ),
    actions=(
        SimulatedAction(
            kind=SimulatedActionKind.UPGRADE,
            actor="0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            target="0xcccccccccccccccccccccccccccccccccccccccc",
            description="upgradeTo(maliciousImplementation)",
        ),
    ),
    scenarios=(
        proxy_upgrade_scenario(
            _base_context(
                proxy_address="0xcccccccccccccccccccccccccccccccccccccccc",
                implementation_address="0xdddddddddddddddddddddddddddddddddddddddd",
                new_implementation_address="0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee",
            )
        ),
    ),
    expected_state_changes=("EIP-1967 implementation slot update",),
    expected_evidence=(
        ExpectedOutcome("implementation_changed", "Proxy implementation storage changed", "high"),
        ExpectedOutcome("proxy_execution", "Delegated execution through proxy", "medium"),
    ),
    limitations=("Does not verify new implementation bytecode safety.",),
)


GOVERNANCE_CAPTURE = AttackScenario(
    attack_id="attack:governance_capture",
    attack_type=AttackType.GOVERNANCE_CAPTURE,
    name="Governance Capture",
    description="Attacker seizes ownership and executes governance proposals.",
    preconditions=(
        ScenarioPrecondition("voting_power", "Attacker accumulated sufficient voting power"),
        ScenarioPrecondition("proposal_passed", "Malicious proposal passed"),
    ),
    actions=(
        SimulatedAction(
            kind=SimulatedActionKind.CALL,
            actor="0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            target="0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
            description="transferOwnership(attacker)",
        ),
        SimulatedAction(
            kind=SimulatedActionKind.GOVERNANCE_EXECUTE,
            actor="0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            target="0x1111111111111111111111111111111111111111",
            description="execute malicious proposal",
        ),
    ),
    scenarios=(
        ownership_transfer_scenario(
            _base_context(
                owner_address="0x2222222222222222222222222222222222222222",
                new_owner_address="0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            )
        ),
        governance_proposal_execution_scenario(
            _base_context(
                governor_address="0x1111111111111111111111111111111111111111",
                recipient_address="0x3333333333333333333333333333333333333333",
                token_address="0x4444444444444444444444444444444444444444",
                treasury_address="0x5555555555555555555555555555555555555555",
            )
        ),
    ),
    expected_state_changes=("Owner slot update", "Treasury balance drain"),
    expected_evidence=(
        ExpectedOutcome("owner_changed", "Ownership transferred to attacker", "high"),
        ExpectedOutcome("governance_execution", "Governance proposal executed", "high"),
    ),
    limitations=("Vote buying and social engineering paths are not modeled.",),
)


TREASURY_DRAIN = AttackScenario(
    attack_id="attack:treasury_drain",
    attack_type=AttackType.TREASURY_DRAIN,
    name="Treasury Drain",
    description="Attacker obtains unlimited approval then drains treasury tokens.",
    preconditions=(
        ScenarioPrecondition("treasury_approval", "Treasury granted token allowance to vulnerable contract"),
    ),
    actions=(
        SimulatedAction(
            kind=SimulatedActionKind.APPROVE,
            actor="0x5555555555555555555555555555555555555555",
            target="0x4444444444444444444444444444444444444444",
            description="treasury approves attacker contract",
        ),
        SimulatedAction(
            kind=SimulatedActionKind.TRANSFER,
            actor="0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            target="0x4444444444444444444444444444444444444444",
            description="transferFrom treasury",
        ),
    ),
    scenarios=(
        unlimited_approval_scenario(
            _base_context(
                token_address="0x4444444444444444444444444444444444444444",
                actor_address="0x5555555555555555555555555555555555555555",
                spender_address="0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            )
        ),
    ),
    expected_state_changes=("Unlimited allowance granted", "Treasury balance reduced"),
    expected_evidence=(
        ExpectedOutcome("unlimited_allowance_granted", "Unlimited token approval", "high"),
    ),
    limitations=("Requires existing treasury approval path; flash-loan paths excluded.",),
)


UNLIMITED_MINT_ATTACK = AttackScenario(
    attack_id="attack:unlimited_mint",
    attack_type=AttackType.UNLIMITED_MINT,
    name="Unlimited Mint Attack",
    description="Privileged actor mints excessive token supply.",
    preconditions=(ScenarioPrecondition("minter_role", "Attacker holds minter role"),),
    actions=(
        SimulatedAction(
            kind=SimulatedActionKind.MINT,
            actor="0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            target="0x4444444444444444444444444444444444444444",
            description="mint(attacker, largeAmount)",
        ),
    ),
    scenarios=(
        unlimited_mint_scenario(
            _base_context(
                token_address="0x4444444444444444444444444444444444444444",
                recipient_address="0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            )
        ),
    ),
    expected_state_changes=("Large supply inflation", "Recipient balance increase"),
    expected_evidence=(
        ExpectedOutcome("large_supply_inflation", "Token supply inflated", "high"),
        ExpectedOutcome("supply_mint", "Supply mint detected", "medium"),
    ),
    limitations=("Mint cap enforcement is not evaluated.",),
)


UNLIMITED_APPROVAL_ATTACK = AttackScenario(
    attack_id="attack:unlimited_approval",
    attack_type=AttackType.UNLIMITED_APPROVAL,
    name="Unlimited Approval Attack",
    description="User tricked into granting unlimited token allowance.",
    preconditions=(ScenarioPrecondition("user_interaction", "Victim signs approval transaction"),),
    actions=(
        SimulatedAction(
            kind=SimulatedActionKind.APPROVE,
            actor="0x2222222222222222222222222222222222222222",
            target="0x4444444444444444444444444444444444444444",
            description="approve(spender, max)",
        ),
    ),
    scenarios=(
        unlimited_approval_scenario(
            _base_context(
                token_address="0x4444444444444444444444444444444444444444",
                actor_address="0x2222222222222222222222222222222222222222",
                spender_address="0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            )
        ),
    ),
    expected_state_changes=("Allowance set to max uint256",),
    expected_evidence=(ExpectedOutcome("unlimited_allowance_granted", "Unlimited approval granted", "high"),),
    limitations=("Phishing and UI deception vectors are out of scope.",),
)


ORACLE_MANIPULATION = AttackScenario(
    attack_id="attack:oracle_manipulation",
    attack_type=AttackType.ORACLE_MANIPULATION,
    name="Oracle Manipulation",
    description="Attacker manipulates oracle storage to distort pricing.",
    preconditions=(
        ScenarioPrecondition("oracle_writable", "Oracle price slot is writable by attacker"),
    ),
    actions=(
        SimulatedAction(
            kind=SimulatedActionKind.STORAGE_WRITE,
            actor="0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            target="0x6666666666666666666666666666666666666666",
            description="write manipulated price to oracle slot",
        ),
    ),
    scenarios=(
        timelock_reduction_scenario(
            _base_context(
                contract_address="0x6666666666666666666666666666666666666666",
                timelock_address="0x6666666666666666666666666666666666666666",
            )
        ),
    ),
    expected_state_changes=("Critical configuration slot modified",),
    expected_evidence=(ExpectedOutcome("simulated_oracle_manipulation", "Oracle configuration changed", "high"),),
    limitations=("TWAP and multi-block manipulation not modeled.",),
)


BRIDGE_COMPROMISE = AttackScenario(
    attack_id="attack:bridge_compromise",
    attack_type=AttackType.BRIDGE_COMPROMISE,
    name="Bridge Compromise",
    description="Bridge validator set compromised leading to unauthorized mint/burn.",
    preconditions=(
        ScenarioPrecondition("validator_keys", "Attacker controls bridge validator quorum"),
    ),
    actions=(
        SimulatedAction(
            kind=SimulatedActionKind.MINT,
            actor="0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            target="0x7777777777777777777777777777777777777777",
            description="bridge mint on destination chain",
        ),
    ),
    scenarios=(
        unlimited_mint_scenario(
            _base_context(
                contract_address="0x7777777777777777777777777777777777777777",
                token_address="0x7777777777777777777777777777777777777777",
                bridge_address="0x8888888888888888888888888888888888888888",
            )
        ),
    ),
    expected_state_changes=("Wrapped asset supply inflation",),
    expected_evidence=(ExpectedOutcome("large_supply_inflation", "Bridge asset supply inflated", "high"),),
    limitations=("Cross-chain message passing is not simulated.",),
)


PRIVILEGE_ESCALATION = AttackScenario(
    attack_id="attack:privilege_escalation",
    attack_type=AttackType.PRIVILEGE_ESCALATION,
    name="Privilege Escalation",
    description="Attacker gains admin role through misconfigured access control.",
    preconditions=(
        ScenarioPrecondition("role_grantable", "Attacker can grant themselves admin role"),
    ),
    actions=(
        SimulatedAction(
            kind=SimulatedActionKind.CALL,
            actor="0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            target="0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
            description="grantRole(DEFAULT_ADMIN_ROLE, attacker)",
        ),
    ),
    scenarios=(
        ownership_transfer_scenario(
            _base_context(
                owner_address="0x2222222222222222222222222222222222222222",
                new_owner_address="0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            )
        ),
    ),
    expected_state_changes=("Admin role or owner slot updated",),
    expected_evidence=(ExpectedOutcome("owner_changed", "Administrative privilege escalated", "high"),),
    limitations=("Role hierarchy and timelock guards are simplified.",),
)


ATTACK_LIBRARY: dict[AttackType, AttackScenario] = {
    AttackType.UPGRADE_ATTACK: UPGRADE_ATTACK,
    AttackType.GOVERNANCE_CAPTURE: GOVERNANCE_CAPTURE,
    AttackType.TREASURY_DRAIN: TREASURY_DRAIN,
    AttackType.UNLIMITED_MINT: UNLIMITED_MINT_ATTACK,
    AttackType.UNLIMITED_APPROVAL: UNLIMITED_APPROVAL_ATTACK,
    AttackType.ORACLE_MANIPULATION: ORACLE_MANIPULATION,
    AttackType.BRIDGE_COMPROMISE: BRIDGE_COMPROMISE,
    AttackType.PRIVILEGE_ESCALATION: PRIVILEGE_ESCALATION,
}

ALL_ATTACKS: tuple[AttackScenario, ...] = tuple(ATTACK_LIBRARY.values())
