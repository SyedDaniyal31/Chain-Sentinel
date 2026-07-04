"""Predict runtime execution reports from simulation scenarios (M9.4)."""

from __future__ import annotations

from app.blockchain.runtime.calltrace import TraceIntelligenceEngine
from app.blockchain.runtime.calltrace.models import CallType, RawExecutionTrace, RawTraceNode, RuntimeExecutionReport
from app.blockchain.runtime.simulation.models import ScenarioType, SimulationScenario
from app.blockchain.runtime.simulation.scenario import simulation_transaction_hash

UPGRADE_SELECTOR = bytes.fromhex("3659cfe6")


class ExecutionPredictor:
    """Compose M9.2 trace intelligence to predict execution outcomes."""

    def __init__(self, trace_engine: TraceIntelligenceEngine | None = None) -> None:
        self._trace_engine = trace_engine or TraceIntelligenceEngine()

    async def predict(self, scenario: SimulationScenario) -> RuntimeExecutionReport:
        trace = _build_trace(scenario)
        return await self._trace_engine.analyze_trace(trace)


def _build_trace(scenario: SimulationScenario) -> RawExecutionTrace:
    tx_hash = simulation_transaction_hash(scenario.scenario_id)
    root = _trace_root_for_scenario(scenario)
    return RawExecutionTrace(
        transaction_hash=tx_hash,
        root=root,
        provider_name="simulation",
        chain_id=scenario.context.chain_id,
    )


def _trace_root_for_scenario(scenario: SimulationScenario) -> RawTraceNode:
    actor = scenario.context.actor_address.lower()
    contract = scenario.context.contract_address.lower()

    if scenario.scenario_type == ScenarioType.PROXY_UPGRADE:
        proxy = (scenario.context.proxy_address or contract).lower()
        new_impl = (
            scenario.context.new_implementation_address
            or scenario.context.implementation_address
            or actor
        ).lower()
        return _node(
            from_address=actor,
            to_address=proxy,
            gas_used=150_000,
            input_data=UPGRADE_SELECTOR + b"\x00" * 28,
            children=(
                _node(
                    call_type=CallType.DELEGATECALL,
                    from_address=proxy,
                    to_address=new_impl,
                    gas_used=100_000,
                ),
            ),
        )

    if scenario.scenario_type == ScenarioType.GOVERNANCE_PROPOSAL_EXECUTION:
        governor = (scenario.context.governor_address or contract).lower()
        target = (scenario.context.recipient_address or contract).lower()
        return _node(
            from_address=actor,
            to_address=governor,
            gas_used=250_000,
            children=(
                _node(from_address=governor, to_address=target, gas_used=120_000),
            ),
        )

    if scenario.scenario_type in {
        ScenarioType.UNLIMITED_APPROVAL,
        ScenarioType.UNLIMITED_MINT,
        ScenarioType.BURN,
        ScenarioType.OWNERSHIP_TRANSFER,
        ScenarioType.PAUSE,
        ScenarioType.UNPAUSE,
        ScenarioType.TIMELOCK_REDUCTION,
    }:
        target = _primary_target(scenario)
        return _node(from_address=actor, to_address=target, gas_used=80_000)

    return _node(from_address=actor, to_address=contract, gas_used=50_000)


def _primary_target(scenario: SimulationScenario) -> str:
    if scenario.scenario_type in {ScenarioType.UNLIMITED_APPROVAL, ScenarioType.UNLIMITED_MINT, ScenarioType.BURN}:
        return (scenario.context.token_address or scenario.context.contract_address).lower()
    if scenario.scenario_type == ScenarioType.TIMELOCK_REDUCTION:
        return (scenario.context.timelock_address or scenario.context.contract_address).lower()
    return scenario.context.contract_address.lower()


def _node(
    *,
    call_type: CallType = CallType.CALL,
    from_address: str,
    to_address: str | None,
    gas_used: int,
    input_data: bytes = b"",
    children: tuple[RawTraceNode, ...] = (),
) -> RawTraceNode:
    return RawTraceNode(
        call_type=call_type,
        from_address=from_address.lower(),
        to_address=to_address.lower() if to_address else None,
        value_wei=0,
        gas=gas_used,
        gas_used=gas_used,
        input=input_data,
        output=b"",
        children=children,
    )
