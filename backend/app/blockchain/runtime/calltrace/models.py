"""Runtime call trace domain models (M9.2)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from app.blockchain.risk.models import RiskEvidence


class CallType(StrEnum):
    """EVM call opcode classification."""

    CALL = "CALL"
    STATICCALL = "STATICCALL"
    DELEGATECALL = "DELEGATECALL"
    CALLCODE = "CALLCODE"
    CREATE = "CREATE"
    CREATE2 = "CREATE2"
    SELFDESTRUCT = "SELFDESTRUCT"


class RuntimeEventType(StrEnum):
    """High-level runtime execution event."""

    DELEGATECALL_CHAIN = "delegatecall_chain"
    PROXY_EXECUTION = "proxy_execution"
    RECURSIVE_CALL = "recursive_call"
    UNEXPECTED_EXTERNAL_CALL = "unexpected_external_call"
    FLASH_LOAN_CALLBACK = "flash_loan_callback"
    CONTRACT_CREATION = "contract_creation"
    CONTRACT_DESTRUCTION = "contract_destruction"


class CallClassification(StrEnum):
    """Semantic classification for a runtime call frame."""

    TOP_LEVEL = "top_level"
    INTERNAL = "internal"
    EXTERNAL = "external"
    DELEGATE = "delegate"
    STATIC = "static"
    CREATION = "creation"
    DESTRUCTION = "destruction"
    VALUE_TRANSFER = "value_transfer"


@dataclass(frozen=True, slots=True)
class RawTraceNode:
    """Provider-agnostic normalized execution trace node."""

    call_type: CallType
    from_address: str
    to_address: str | None
    value_wei: int
    gas: int
    gas_used: int
    input: bytes
    output: bytes
    error: str | None = None
    revert_reason: str | None = None
    children: tuple[RawTraceNode, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class RawExecutionTrace:
    """Normalized execution trace returned by a trace provider."""

    transaction_hash: str
    root: RawTraceNode
    provider_name: str
    chain_id: int | None = None


@dataclass(frozen=True, slots=True)
class RuntimeCallNode:
    """Single node in a runtime call graph."""

    node_id: str
    parent_id: str | None
    depth: int
    order_index: int
    call_type: CallType
    classification: CallClassification
    from_address: str
    to_address: str | None
    value_wei: int
    gas: int
    gas_used: int
    input: bytes
    output: bytes
    selector: str | None
    error: str | None
    revert_reason: str | None


@dataclass(frozen=True, slots=True)
class RuntimeCallGraph:
    """Deterministic runtime call graph."""

    root_id: str
    nodes: tuple[RuntimeCallNode, ...]
    execution_order: tuple[str, ...]
    max_depth: int


@dataclass(frozen=True, slots=True)
class RuntimeEvent:
    """Detected runtime execution event."""

    event_type: RuntimeEventType
    node_id: str
    description: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class RevertFinding:
    """Single revert captured in the execution trace."""

    node_id: str
    contract_address: str | None
    failing_function: str | None
    revert_reason: str | None
    call_depth: int
    execution_path: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RevertAnalysis:
    """Aggregate revert analysis for an execution trace."""

    has_revert: bool
    findings: tuple[RevertFinding, ...]


@dataclass(frozen=True, slots=True)
class GasCallStat:
    """Gas usage for a single call frame."""

    node_id: str
    call_type: CallType
    to_address: str | None
    selector: str | None
    gas_used: int
    depth: int


@dataclass(frozen=True, slots=True)
class GasProfile:
    """Gas profiling summary for an execution trace."""

    total_gas_used: int
    call_stats: tuple[GasCallStat, ...]
    hottest_functions: tuple[tuple[str, int], ...]
    deepest_path: tuple[str, ...]
    deepest_depth: int
    expensive_external_calls: tuple[GasCallStat, ...]


@dataclass(frozen=True, slots=True)
class RuntimeExecutionReport:
    """Runtime execution intelligence output."""

    transaction_hash: str
    call_graph: RuntimeCallGraph
    runtime_events: tuple[RuntimeEvent, ...]
    revert_analysis: RevertAnalysis
    gas_profile: GasProfile
    risk_evidence: tuple[RiskEvidence, ...]
    provider_name: str
