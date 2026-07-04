"""Runtime call trace intelligence orchestrator (M9.2)."""

from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal
from typing import Any

from app.blockchain.risk.evidence import create_evidence, merge_evidence
from app.blockchain.risk.evidence_types import (
    EvidenceCategory,
    EvidenceMetadataKey,
    EvidenceSeverity,
    EvidenceSource,
)
from app.blockchain.risk.models import RiskEvidence
from app.blockchain.runtime.calltrace.call_graph_builder import CallGraphBuilder
from app.blockchain.runtime.calltrace.gas_profiler import GasProfiler
from app.blockchain.runtime.calltrace.models import (
    RawExecutionTrace,
    RawTraceNode,
    RevertAnalysis,
    RuntimeEvent,
    RuntimeEventType,
    RuntimeExecutionReport,
)
from app.blockchain.runtime.calltrace.revert_analyzer import RevertAnalyzer
from app.blockchain.runtime.calltrace.runtime_event_analyzer import RuntimeEventAnalyzer
from app.blockchain.runtime.calltrace.trace_decoder import TraceDecoder
from app.blockchain.runtime.calltrace.trace_provider import TraceProvider
from app.models.enums import ConfidenceLevel


class TraceIntelligenceEngine:
    """Analyze execution traces and emit standardized runtime risk evidence."""

    def __init__(
        self,
        trace_provider: TraceProvider | None = None,
        graph_builder: CallGraphBuilder | None = None,
        event_analyzer: RuntimeEventAnalyzer | None = None,
        revert_analyzer: RevertAnalyzer | None = None,
        gas_profiler: GasProfiler | None = None,
    ) -> None:
        self._trace_provider = trace_provider
        self._graph_builder = graph_builder or CallGraphBuilder()
        self._event_analyzer = event_analyzer or RuntimeEventAnalyzer()
        self._revert_analyzer = revert_analyzer or RevertAnalyzer()
        self._gas_profiler = gas_profiler or GasProfiler()

    async def analyze_trace(
        self,
        trace: RawExecutionTrace | RawTraceNode | Mapping[str, Any],
        *,
        transaction_hash: str | None = None,
        chain_id: int | None = None,
        trusted_addresses: set[str] | None = None,
    ) -> RuntimeExecutionReport:
        normalized = _normalize_trace(trace, transaction_hash=transaction_hash, chain_id=chain_id)
        graph = self._graph_builder.build(normalized.root)
        runtime_events = self._event_analyzer.analyze(graph, trusted_addresses=trusted_addresses)
        revert_analysis = self._revert_analyzer.analyze(graph)
        gas_profile = self._gas_profiler.profile(graph)
        evidence = emit_trace_evidence(
            transaction_hash=normalized.transaction_hash,
            runtime_events=runtime_events,
            revert_analysis=revert_analysis,
            gas_profile=gas_profile,
        )

        return RuntimeExecutionReport(
            transaction_hash=normalized.transaction_hash,
            call_graph=graph,
            runtime_events=runtime_events,
            revert_analysis=revert_analysis,
            gas_profile=gas_profile,
            risk_evidence=tuple(evidence),
            provider_name=normalized.provider_name,
        )

    async def analyze_hash(
        self,
        transaction_hash: str,
        *,
        chain_id: int = 1,
        trusted_addresses: set[str] | None = None,
    ) -> RuntimeExecutionReport:
        if self._trace_provider is None:
            raise ValueError("trace provider is required for hash-based analysis")
        trace = await self._trace_provider.get_execution_trace(
            transaction_hash,
            chain_id=chain_id,
        )
        return await self.analyze_trace(
            trace,
            trusted_addresses=trusted_addresses,
        )


def emit_trace_evidence(
    *,
    transaction_hash: str,
    runtime_events: tuple[RuntimeEvent, ...],
    revert_analysis: RevertAnalysis,
    gas_profile: Any,
) -> list[RiskEvidence]:
    """Convert runtime execution findings into standardized M7 RiskEvidence."""
    groups: list[list[RiskEvidence]] = []

    groups.append(_runtime_event_evidence(transaction_hash, runtime_events))
    groups.append(_revert_evidence(transaction_hash, revert_analysis))
    groups.append(_gas_evidence(transaction_hash, gas_profile))

    return merge_evidence(*groups)


def _runtime_event_evidence(
    transaction_hash: str,
    runtime_events: tuple[RuntimeEvent, ...],
) -> list[RiskEvidence]:
    evidence: list[RiskEvidence] = []
    for event in runtime_events:
        mapping = _event_evidence_mapping(event)
        if mapping is None:
            continue
        source, category, signal, severity, reason = mapping
        evidence.append(
            create_evidence(
                source=source,
                category=category,
                signal=signal,
                severity=severity,
                score=Decimal("0.00"),
                confidence=ConfidenceLevel.HIGH,
                reason=reason,
                metadata={
                    EvidenceMetadataKey.SIGNAL.value: signal,
                    EvidenceMetadataKey.REASON_ONLY.value: True,
                    "transaction_hash": transaction_hash,
                    "node_id": event.node_id,
                    **event.metadata,
                },
            )
        )
    return evidence


def _event_evidence_mapping(
    event: RuntimeEvent,
) -> tuple[EvidenceSource, EvidenceCategory, str, EvidenceSeverity, str] | None:
    mappings: dict[RuntimeEventType, tuple[EvidenceSource, EvidenceCategory, str, EvidenceSeverity, str]] = {
        RuntimeEventType.DELEGATECALL_CHAIN: (
            EvidenceSource.PROXY,
            EvidenceCategory.UPGRADEABILITY,
            "delegatecall_chain",
            EvidenceSeverity.HIGH,
            "Delegatecall chain detected in execution trace",
        ),
        RuntimeEventType.PROXY_EXECUTION: (
            EvidenceSource.PROXY,
            EvidenceCategory.UPGRADEABILITY,
            "proxy_execution",
            EvidenceSeverity.MEDIUM,
            "Proxy delegated execution detected in runtime trace",
        ),
        RuntimeEventType.RECURSIVE_CALL: (
            EvidenceSource.THREAT_SURFACE,
            EvidenceCategory.THREAT,
            "recursive_execution",
            EvidenceSeverity.MEDIUM,
            "Deep recursive execution pattern detected",
        ),
        RuntimeEventType.UNEXPECTED_EXTERNAL_CALL: (
            EvidenceSource.THREAT_SURFACE,
            EvidenceCategory.THREAT,
            "unexpected_external_call",
            EvidenceSeverity.HIGH,
            "Unexpected external call detected during execution",
        ),
        RuntimeEventType.FLASH_LOAN_CALLBACK: (
            EvidenceSource.PROTOCOL,
            EvidenceCategory.PROTOCOL,
            "flash_loan_callback",
            EvidenceSeverity.MEDIUM,
            "Flash-loan callback execution pattern detected",
        ),
        RuntimeEventType.CONTRACT_CREATION: (
            EvidenceSource.CLASSIFICATION,
            EvidenceCategory.CLASSIFICATION,
            "runtime_create",
            EvidenceSeverity.MEDIUM,
            "Contract creation detected in execution trace",
        ),
        RuntimeEventType.CONTRACT_DESTRUCTION: (
            EvidenceSource.CAPABILITY,
            EvidenceCategory.CAPABILITY,
            "runtime_selfdestruct",
            EvidenceSeverity.HIGH,
            "Contract selfdestruct executed in runtime trace",
        ),
    }
    return mappings.get(event.event_type)


def _revert_evidence(
    transaction_hash: str,
    revert_analysis: RevertAnalysis,
) -> list[RiskEvidence]:
    if not revert_analysis.has_revert:
        return []
    finding = revert_analysis.findings[0]
    return [
        create_evidence(
            source=EvidenceSource.SYSTEM,
            category=EvidenceCategory.SYSTEM,
            signal="execution_revert",
            severity=EvidenceSeverity.MEDIUM,
            score=Decimal("0.00"),
            confidence=ConfidenceLevel.HIGH,
            reason="Execution revert captured in runtime trace",
            metadata={
                EvidenceMetadataKey.SIGNAL.value: "execution_revert",
                EvidenceMetadataKey.REASON_ONLY.value: True,
                "transaction_hash": transaction_hash,
                "node_id": finding.node_id,
                "revert_reason": finding.revert_reason,
                "failing_function": finding.failing_function,
                "execution_path": list(finding.execution_path),
            },
        )
    ]


def _gas_evidence(transaction_hash: str, gas_profile: Any) -> list[RiskEvidence]:
    if gas_profile.deepest_depth < 4:
        return []
    return [
        create_evidence(
            source=EvidenceSource.THREAT_SURFACE,
            category=EvidenceCategory.THREAT,
            signal="deep_execution_path",
            severity=EvidenceSeverity.LOW,
            score=Decimal("0.00"),
            confidence=ConfidenceLevel.MEDIUM,
            reason="Deep execution path observed in runtime trace",
            metadata={
                EvidenceMetadataKey.SIGNAL.value: "deep_execution_path",
                EvidenceMetadataKey.REASON_ONLY.value: True,
                "transaction_hash": transaction_hash,
                "deepest_depth": gas_profile.deepest_depth,
                "deepest_path": list(gas_profile.deepest_path),
            },
        )
    ]


def _normalize_trace(
    trace: RawExecutionTrace | RawTraceNode | Mapping[str, Any],
    *,
    transaction_hash: str | None,
    chain_id: int | None,
) -> RawExecutionTrace:
    if isinstance(trace, RawExecutionTrace):
        return trace
    if isinstance(trace, RawTraceNode):
        return RawExecutionTrace(
            transaction_hash=(transaction_hash or "0x" + ("00" * 32)).lower(),
            root=trace,
            provider_name="inline",
            chain_id=chain_id,
        )
    return TraceDecoder.decode_trace(
        trace,
        transaction_hash=transaction_hash or str(trace.get("transactionHash", "0x" + ("00" * 32))),
        provider_name=str(trace.get("provider_name", "decoded")),
        chain_id=chain_id,
    )
