"""Unit tests for runtime call trace intelligence (M9.2)."""

from __future__ import annotations

import pytest

from app.blockchain.risk.evidence_types import EvidenceMetadataKey, EvidenceSeverity, EvidenceSource
from app.blockchain.runtime.calltrace import (
    CallType,
    RawExecutionTrace,
    RawTraceNode,
    RuntimeEventType,
    StaticTraceProvider,
    TraceDecoder,
    TraceIntelligenceEngine,
    emit_trace_evidence,
)

SENDER = "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
RECIPIENT = "0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
PROXY = "0xcccccccccccccccccccccccccccccccccccccccc"
IMPLEMENTATION = "0xdddddddddddddddddddddddddddddddddddddddd"
TOKEN = "0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee"
ATTACKER = "0x1111111111111111111111111111111111111111"
CREATED = "0x2222222222222222222222222222222222222222"
TX_HASH = "0x" + "cd" * 32


def _node(
    *,
    call_type: CallType = CallType.CALL,
    from_address: str = SENDER,
    to_address: str | None = RECIPIENT,
    value_wei: int = 0,
    gas_used: int = 21_000,
    input_data: bytes = b"",
    error: str | None = None,
    revert_reason: str | None = None,
    children: tuple[RawTraceNode, ...] = (),
) -> RawTraceNode:
    return RawTraceNode(
        call_type=call_type,
        from_address=from_address.lower(),
        to_address=to_address.lower() if to_address else None,
        value_wei=value_wei,
        gas=gas_used,
        gas_used=gas_used,
        input=input_data,
        output=b"",
        error=error,
        revert_reason=revert_reason,
        children=children,
    )


def _trace(root: RawTraceNode) -> RawExecutionTrace:
    return RawExecutionTrace(
        transaction_hash=TX_HASH,
        root=root,
        provider_name="test",
        chain_id=1,
    )


@pytest.mark.asyncio
async def test_simple_transfer_call_graph() -> None:
    trace = _trace(_node(value_wei=10**18, gas_used=21_000))
    report = await TraceIntelligenceEngine().analyze_trace(trace)

    assert len(report.call_graph.nodes) == 1
    assert report.call_graph.nodes[0].value_wei == 10**18
    assert report.call_graph.max_depth == 0
    assert report.gas_profile.total_gas_used == 21_000


@pytest.mark.asyncio
async def test_proxy_execution_detection() -> None:
    trace = _trace(
        _node(
            from_address=SENDER,
            to_address=PROXY,
            gas_used=120_000,
            children=(
                _node(
                    call_type=CallType.DELEGATECALL,
                    from_address=PROXY,
                    to_address=IMPLEMENTATION,
                    gas_used=90_000,
                ),
            ),
        )
    )
    report = await TraceIntelligenceEngine().analyze_trace(trace)

    event_types = {event.event_type for event in report.runtime_events}
    assert RuntimeEventType.PROXY_EXECUTION in event_types
    signals = {item.metadata.get(EvidenceMetadataKey.SIGNAL.value) for item in report.risk_evidence}
    assert "proxy_execution" in signals


@pytest.mark.asyncio
async def test_delegatecall_chain_detection() -> None:
    trace = _trace(
        _node(
            to_address=PROXY,
            gas_used=150_000,
            children=(
                _node(
                    call_type=CallType.DELEGATECALL,
                    from_address=PROXY,
                    to_address=IMPLEMENTATION,
                    gas_used=80_000,
                    children=(
                        _node(
                            call_type=CallType.DELEGATECALL,
                            from_address=IMPLEMENTATION,
                            to_address=ATTACKER,
                            gas_used=40_000,
                        ),
                    ),
                ),
            ),
        )
    )
    report = await TraceIntelligenceEngine().analyze_trace(trace)

    assert RuntimeEventType.DELEGATECALL_CHAIN in {
        event.event_type for event in report.runtime_events
    }
    assert any(
        item.metadata.get(EvidenceMetadataKey.SIGNAL.value) == "delegatecall_chain"
        for item in report.risk_evidence
    )


@pytest.mark.asyncio
async def test_create2_deployment_detection() -> None:
    trace = _trace(
        _node(
            gas_used=200_000,
            children=(
                _node(
                    call_type=CallType.CREATE2,
                    from_address=SENDER,
                    to_address=CREATED,
                    gas_used=180_000,
                ),
            ),
        )
    )
    report = await TraceIntelligenceEngine().analyze_trace(trace)

    assert RuntimeEventType.CONTRACT_CREATION in {
        event.event_type for event in report.runtime_events
    }
    assert any(
        item.metadata.get(EvidenceMetadataKey.SIGNAL.value) == "runtime_create"
        for item in report.risk_evidence
    )


@pytest.mark.asyncio
async def test_selfdestruct_detection() -> None:
    trace = _trace(
        _node(
            gas_used=50_000,
            children=(
                _node(
                    call_type=CallType.SELFDESTRUCT,
                    from_address=TOKEN,
                    to_address=SENDER,
                    gas_used=5_000,
                ),
            ),
        )
    )
    report = await TraceIntelligenceEngine().analyze_trace(trace)

    assert RuntimeEventType.CONTRACT_DESTRUCTION in {
        event.event_type for event in report.runtime_events
    }
    assert any(
        item.metadata.get(EvidenceMetadataKey.SIGNAL.value) == "runtime_selfdestruct"
        for item in report.risk_evidence
    )


@pytest.mark.asyncio
async def test_revert_analysis() -> None:
    trace = _trace(
        _node(
            to_address=TOKEN,
            gas_used=80_000,
            children=(
                _node(
                    to_address=TOKEN,
                    gas_used=50_000,
                    input_data=bytes.fromhex("095ea7b3") + b"\x00" * 32,
                    error="revert",
                    revert_reason="ERC20: insufficient allowance",
                ),
            ),
        )
    )
    report = await TraceIntelligenceEngine().analyze_trace(trace)

    assert report.revert_analysis.has_revert is True
    finding = report.revert_analysis.findings[0]
    assert finding.revert_reason == "ERC20: insufficient allowance"
    assert finding.failing_function == "095ea7b3"
    assert finding.execution_path[0] == "0"
    assert any(
        item.metadata.get(EvidenceMetadataKey.SIGNAL.value) == "execution_revert"
        for item in report.risk_evidence
    )


@pytest.mark.asyncio
async def test_recursive_execution_detection() -> None:
    recursive_child = _node(
        from_address=TOKEN,
        to_address=ATTACKER,
        gas_used=30_000,
        input_data=bytes.fromhex("70a08231"),
    )
    trace = _trace(
        _node(
            to_address=TOKEN,
            gas_used=100_000,
            children=(
                recursive_child,
                _node(
                    from_address=TOKEN,
                    to_address=ATTACKER,
                    gas_used=25_000,
                    input_data=bytes.fromhex("70a08231"),
                ),
            ),
        )
    )
    report = await TraceIntelligenceEngine().analyze_trace(trace)

    assert RuntimeEventType.RECURSIVE_CALL in {
        event.event_type for event in report.runtime_events
    }


@pytest.mark.asyncio
async def test_gas_profiling() -> None:
    trace = _trace(
        _node(
            gas_used=50_000,
            children=(
                _node(to_address=TOKEN, gas_used=150_000, input_data=bytes.fromhex("a9059cbb")),
                _node(
                    to_address=ATTACKER,
                    gas_used=250_000,
                    input_data=bytes.fromhex("23b872dd"),
                    children=(
                        _node(to_address=RECIPIENT, gas_used=80_000),
                        _node(to_address=RECIPIENT, gas_used=70_000),
                    ),
                ),
            ),
        )
    )
    report = await TraceIntelligenceEngine().analyze_trace(trace)

    assert report.gas_profile.total_gas_used > 0
    assert report.gas_profile.hottest_functions
    assert len(report.gas_profile.deepest_path) >= 2
    assert report.gas_profile.expensive_external_calls


@pytest.mark.asyncio
async def test_trace_decoder_supports_provider_payload() -> None:
    payload = {
        "type": "CALL",
        "from": SENDER,
        "to": PROXY,
        "value": "0x0",
        "gas": "0x5208",
        "gasUsed": "0x186a0",
        "input": "0x",
        "calls": [
            {
                "type": "DELEGATECALL",
                "from": PROXY,
                "to": IMPLEMENTATION,
                "value": "0x0",
                "gas": "0x7530",
                "gasUsed": "0x2710",
                "input": "0x",
            }
        ],
    }
    trace = TraceDecoder.decode_trace(payload, transaction_hash=TX_HASH, provider_name="geth")
    report = await TraceIntelligenceEngine().analyze_trace(trace)

    assert report.provider_name == "geth"
    assert len(report.call_graph.nodes) == 2


@pytest.mark.asyncio
async def test_hash_analysis_via_static_provider() -> None:
    trace = _trace(_node(to_address=PROXY, gas_used=60_000))
    provider = StaticTraceProvider({TX_HASH: trace})
    engine = TraceIntelligenceEngine(trace_provider=provider)

    report = await engine.analyze_hash(TX_HASH, chain_id=1)

    assert report.transaction_hash == TX_HASH
    assert report.provider_name == "static"


def test_evidence_generation_does_not_compute_runtime_risk_score() -> None:
    from app.blockchain.runtime.calltrace.models import GasProfile, RevertAnalysis, RuntimeEvent

    evidence = emit_trace_evidence(
        transaction_hash=TX_HASH,
        runtime_events=(
            RuntimeEvent(
                event_type=RuntimeEventType.UNEXPECTED_EXTERNAL_CALL,
                node_id="0.1",
                description="unexpected",
                metadata={"to_address": ATTACKER},
            ),
        ),
        revert_analysis=RevertAnalysis(has_revert=False, findings=()),
        gas_profile=GasProfile(
            total_gas_used=100,
            call_stats=(),
            hottest_functions=(),
            deepest_path=("0",),
            deepest_depth=0,
            expensive_external_calls=(),
        ),
    )

    assert evidence
    assert all(item.score == 0 for item in evidence)
    assert all(item.metadata.get(EvidenceMetadataKey.REASON_ONLY.value) for item in evidence)
    assert any(item.source == EvidenceSource.THREAT_SURFACE for item in evidence)
    assert any(item.severity == EvidenceSeverity.HIGH for item in evidence)


@pytest.mark.asyncio
async def test_deterministic_call_graph_ordering() -> None:
    trace = _trace(
        _node(
            children=(
                _node(to_address=TOKEN, gas_used=10, input_data=bytes.fromhex("a9059cbb")),
                _node(to_address=ATTACKER, gas_used=20, input_data=bytes.fromhex("23b872dd")),
            ),
        )
    )
    report_one = await TraceIntelligenceEngine().analyze_trace(trace)
    report_two = await TraceIntelligenceEngine().analyze_trace(trace)

    assert report_one.call_graph.execution_order == report_two.call_graph.execution_order
    assert [node.node_id for node in report_one.call_graph.nodes] == [
        node.node_id for node in report_two.call_graph.nodes
    ]
