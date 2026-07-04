"""Scenario builder and validation (M9.4)."""

from __future__ import annotations

from app.blockchain.runtime.simulation.models import ScenarioType, SimulationContext, SimulationScenario
from app.blockchain.runtime.simulation.scenario import SCENARIO_FACTORIES


class ScenarioValidationError(ValueError):
    """Raised when a simulation scenario fails validation."""


class ScenarioBuilder:
    """Build and validate immutable simulation scenarios."""

    def build(self, scenario_type: ScenarioType, context: SimulationContext) -> SimulationScenario:
        self.validate(scenario_type, context)
        factory = SCENARIO_FACTORIES.get(scenario_type)
        if factory is None:
            raise ScenarioValidationError(f"unsupported scenario type: {scenario_type.value}")
        return factory(context)  # type: ignore[operator]

    def validate(self, scenario_type: ScenarioType, context: SimulationContext) -> None:
        errors = list(_validation_errors(scenario_type, context))
        if errors:
            raise ScenarioValidationError("; ".join(errors))

    def build_preconditions(self, scenario_type: ScenarioType) -> tuple:
        factory = SCENARIO_FACTORIES.get(scenario_type)
        if factory is None:
            raise ScenarioValidationError(f"unsupported scenario type: {scenario_type.value}")
        placeholder = _placeholder_context(scenario_type)
        return factory(placeholder).preconditions  # type: ignore[operator]


def _placeholder_context(scenario_type: ScenarioType) -> SimulationContext:
    address = "0x" + "aa" * 20
    return SimulationContext(chain_id=1, actor_address=address, contract_address=address)


def _validation_errors(scenario_type: ScenarioType, context: SimulationContext) -> list[str]:
    errors: list[str] = []
    if context.chain_id <= 0:
        errors.append("chain_id must be positive")
    if not _is_address(context.actor_address):
        errors.append("actor_address must be a valid address")
    if not _is_address(context.contract_address):
        errors.append("contract_address must be a valid address")

    if scenario_type == ScenarioType.PROXY_UPGRADE:
        proxy = context.proxy_address or context.contract_address
        if not _is_address(proxy):
            errors.append("proxy_address must be a valid address")
        if context.new_implementation_address and not _is_address(context.new_implementation_address):
            errors.append("new_implementation_address must be a valid address")

    if scenario_type == ScenarioType.OWNERSHIP_TRANSFER:
        if context.new_owner_address and not _is_address(context.new_owner_address):
            errors.append("new_owner_address must be a valid address")

    if scenario_type in {ScenarioType.UNLIMITED_APPROVAL, ScenarioType.UNLIMITED_MINT, ScenarioType.BURN}:
        token = context.token_address or context.contract_address
        if not _is_address(token):
            errors.append("token_address must be a valid address")

    if scenario_type == ScenarioType.UNLIMITED_APPROVAL and context.spender_address:
        if not _is_address(context.spender_address):
            errors.append("spender_address must be a valid address")

    if scenario_type == ScenarioType.TIMELOCK_REDUCTION:
        timelock = context.timelock_address or context.contract_address
        if not _is_address(timelock):
            errors.append("timelock_address must be a valid address")

    if scenario_type == ScenarioType.GOVERNANCE_PROPOSAL_EXECUTION:
        governor = context.governor_address or context.contract_address
        if not _is_address(governor):
            errors.append("governor_address must be a valid address")

    return errors


def _is_address(value: str | None) -> bool:
    if not value:
        return False
    normalized = value.lower().removeprefix("0x")
    return len(normalized) == 40 and all(ch in "0123456789abcdef" for ch in normalized)
