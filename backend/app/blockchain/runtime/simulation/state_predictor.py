"""Predict runtime state reports from simulation scenarios (M9.4)."""

from __future__ import annotations

from app.blockchain.eip1967 import EIP1967_ADMIN_SLOT, EIP1967_IMPLEMENTATION_SLOT
from app.blockchain.runtime.simulation.models import ScenarioType, SimulationScenario
from app.blockchain.runtime.simulation.scenario import PAUSE_SLOT, TIMELOCK_SLOT, simulation_transaction_hash
from app.blockchain.runtime.state import StateTransitionEngine
from app.blockchain.runtime.state.event_state_mapper import TOPIC_APPROVAL, TOPIC_OWNERSHIP_TRANSFERRED, TOPIC_TRANSFER
from app.blockchain.runtime.state.models import (
    BalanceAssetType,
    RawAllowanceDiff,
    RawBalanceDiff,
    RawStateLog,
    RawStateTransition,
    RawStorageDiff,
    RawSupplyDiff,
    RuntimeStateReport,
)
from app.blockchain.runtime.calltrace.models import RuntimeExecutionReport

MAX_UINT256 = (1 << 256) - 1
LARGE_MINT_AMOUNT = 10**25


class StatePredictor:
    """Compose M9.3 state intelligence to predict state transitions."""

    def __init__(self, state_engine: StateTransitionEngine | None = None) -> None:
        self._state_engine = state_engine or StateTransitionEngine()

    async def predict(
        self,
        scenario: SimulationScenario,
        *,
        execution_report: RuntimeExecutionReport | None = None,
    ) -> RuntimeStateReport:
        transition = _build_transition(scenario)
        return await self._state_engine.analyze_transition(
            transition,
            execution_report=execution_report,
        )


def _build_transition(scenario: SimulationScenario) -> RawStateTransition:
    tx_hash = simulation_transaction_hash(scenario.scenario_id)
    builder = _TransitionBuilder(scenario)
    return RawStateTransition(
        transaction_hash=tx_hash,
        block_number=None,
        storage_diffs=builder.storage_diffs(),
        balance_diffs=builder.balance_diffs(),
        allowance_diffs=builder.allowance_diffs(),
        supply_diffs=builder.supply_diffs(),
        logs=builder.logs(),
        provider_name="simulation",
        chain_id=scenario.context.chain_id,
    )


class _TransitionBuilder:
    def __init__(self, scenario: SimulationScenario) -> None:
        self._scenario = scenario
        self._context = scenario.context

    def storage_diffs(self) -> tuple[RawStorageDiff, ...]:
        scenario_type = self._scenario.scenario_type
        contract = self._context.contract_address.lower()

        if scenario_type == ScenarioType.PROXY_UPGRADE:
            proxy = (self._context.proxy_address or contract).lower()
            old_impl = (self._context.implementation_address or contract).lower()
            new_impl = (self._context.new_implementation_address or self._context.actor_address).lower()
            return (
                RawStorageDiff(
                    contract_address=proxy,
                    slot=EIP1967_IMPLEMENTATION_SLOT,
                    before=_word_address(old_impl),
                    after=_word_address(new_impl),
                ),
            )

        if scenario_type == ScenarioType.OWNERSHIP_TRANSFER:
            owner = (self._context.owner_address or self._context.actor_address).lower()
            new_owner = (self._context.new_owner_address or self._context.recipient_address or owner).lower()
            return (
                RawStorageDiff(
                    contract_address=contract,
                    slot="0x0000000000000000000000000000000000000000000000000000000000000000",
                    before=_word_address(owner),
                    after=_word_address(new_owner),
                ),
            )

        if scenario_type == ScenarioType.TIMELOCK_REDUCTION:
            timelock = (self._context.timelock_address or contract).lower()
            return (
                RawStorageDiff(
                    contract_address=timelock,
                    slot=TIMELOCK_SLOT,
                    before=_word_hex(86_400),
                    after=_word_hex(0),
                ),
            )

        if scenario_type == ScenarioType.PAUSE:
            return (
                RawStorageDiff(
                    contract_address=contract,
                    slot=PAUSE_SLOT,
                    before=_word_hex(0),
                    after=_word_hex(1),
                ),
            )

        if scenario_type == ScenarioType.UNPAUSE:
            return (
                RawStorageDiff(
                    contract_address=contract,
                    slot=PAUSE_SLOT,
                    before=_word_hex(1),
                    after=_word_hex(0),
                ),
            )

        if scenario_type == ScenarioType.GOVERNANCE_PROPOSAL_EXECUTION:
            governor = (self._context.governor_address or contract).lower()
            new_owner = (self._context.recipient_address or self._context.actor_address).lower()
            return (
                RawStorageDiff(
                    contract_address=governor,
                    slot="0x0000000000000000000000000000000000000000000000000000000000000000",
                    before=_word_address(self._context.actor_address),
                    after=_word_address(new_owner),
                ),
            )

        return ()

    def balance_diffs(self) -> tuple[RawBalanceDiff, ...]:
        scenario_type = self._scenario.scenario_type
        token = (self._context.token_address or self._context.contract_address).lower()
        actor = self._context.actor_address.lower()
        recipient = (self._context.recipient_address or actor).lower()

        if scenario_type == ScenarioType.UNLIMITED_MINT:
            return (
                RawBalanceDiff(
                    asset_type=BalanceAssetType.ERC20,
                    contract_address=token,
                    account_address=recipient,
                    before=0,
                    after=LARGE_MINT_AMOUNT,
                ),
            )

        if scenario_type == ScenarioType.BURN:
            return (
                RawBalanceDiff(
                    asset_type=BalanceAssetType.ERC20,
                    contract_address=token,
                    account_address=actor,
                    before=1_000,
                    after=500,
                ),
            )

        if scenario_type == ScenarioType.GOVERNANCE_PROPOSAL_EXECUTION:
            treasury = (self._context.treasury_address or recipient).lower()
            return (
                RawBalanceDiff(
                    asset_type=BalanceAssetType.ERC20,
                    contract_address=token,
                    account_address=treasury,
                    before=10**22,
                    after=0,
                ),
            )

        return ()

    def allowance_diffs(self) -> tuple[RawAllowanceDiff, ...]:
        if self._scenario.scenario_type != ScenarioType.UNLIMITED_APPROVAL:
            return ()
        token = (self._context.token_address or self._context.contract_address).lower()
        owner = self._context.actor_address.lower()
        spender = (self._context.spender_address or self._context.recipient_address or owner).lower()
        return (
            RawAllowanceDiff(
                token_address=token,
                owner_address=owner,
                spender_address=spender,
                before=0,
                after=MAX_UINT256,
            ),
        )

    def supply_diffs(self) -> tuple[RawSupplyDiff, ...]:
        token = (self._context.token_address or self._context.contract_address).lower()
        scenario_type = self._scenario.scenario_type

        if scenario_type == ScenarioType.UNLIMITED_MINT:
            return (RawSupplyDiff(token_address=token, before=0, after=LARGE_MINT_AMOUNT),)

        if scenario_type == ScenarioType.BURN:
            return (RawSupplyDiff(token_address=token, before=1_000, after=500),)

        return ()

    def logs(self) -> tuple[RawStateLog, ...]:
        scenario_type = self._scenario.scenario_type
        contract = self._context.contract_address.lower()
        token = (self._context.token_address or contract).lower()
        actor = self._context.actor_address.lower()

        if scenario_type == ScenarioType.OWNERSHIP_TRANSFER:
            owner = (self._context.owner_address or actor).lower()
            new_owner = (self._context.new_owner_address or self._context.recipient_address or actor).lower()
            return (
                RawStateLog(
                    contract_address=contract,
                    topics=(
                        TOPIC_OWNERSHIP_TRANSFERRED,
                        _topic_address(owner),
                        _topic_address(new_owner),
                    ),
                    data=b"",
                ),
            )

        if scenario_type == ScenarioType.UNLIMITED_APPROVAL:
            spender = (self._context.spender_address or self._context.recipient_address or actor).lower()
            return (
                RawStateLog(
                    contract_address=token,
                    topics=(TOPIC_APPROVAL, _topic_address(actor), _topic_address(spender)),
                    data=bytes.fromhex(_uint_word(MAX_UINT256)[2:]),
                ),
            )

        if scenario_type == ScenarioType.UNLIMITED_MINT:
            recipient = (self._context.recipient_address or actor).lower()
            return (
                RawStateLog(
                    contract_address=token,
                    topics=(TOPIC_TRANSFER, _topic_address("0x" + "00" * 20), _topic_address(recipient)),
                    data=bytes.fromhex(_uint_word(LARGE_MINT_AMOUNT)[2:]),
                ),
            )

        if scenario_type == ScenarioType.BURN:
            return (
                RawStateLog(
                    contract_address=token,
                    topics=(TOPIC_TRANSFER, _topic_address(actor), _topic_address("0x" + "00" * 20)),
                    data=bytes.fromhex(_uint_word(500)[2:]),
                ),
            )

        if scenario_type == ScenarioType.PROXY_UPGRADE:
            proxy = (self._context.proxy_address or contract).lower()
            old_impl = (self._context.implementation_address or contract).lower()
            new_impl = (self._context.new_implementation_address or actor).lower()
            return (
                RawStateLog(
                    contract_address=proxy,
                    topics=(
                        "0xbc7cd75a20ee27fd9adebab32041f755214dbc6b556c695889b9856025e1d5e8",
                        _topic_address(old_impl),
                        _topic_address(new_impl),
                    ),
                    data=b"",
                ),
            )

        return ()


def _word_address(address: str) -> str:
    return "0x" + address.lower().removeprefix("0x").rjust(64, "0")


def _topic_address(address: str) -> str:
    return _word_address(address)


def _word_hex(value: int) -> str:
    return "0x" + format(value, "064x")


def _uint_word(value: int) -> str:
    return _word_hex(value)
