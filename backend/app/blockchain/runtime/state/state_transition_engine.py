"""State transition intelligence orchestrator (M9.3)."""

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
from app.blockchain.runtime.calltrace.models import RuntimeExecutionReport
from app.blockchain.runtime.state.models import (
    AllowanceChange,
    AllowanceChangeKind,
    OwnershipChange,
    OwnershipRole,
    RawStateTransition,
    RuntimeStateReport,
    StorageDiff,
    StorageSlotKind,
    SupplyChange,
    SupplyChangeKind,
)
from app.blockchain.runtime.state.state_decoder import StateTransitionDecoder
from app.blockchain.runtime.state.state_diff_builder import StateDiffBuilder, StateDiffBundle
from app.blockchain.runtime.state.state_provider import StateTransitionProvider
from app.models.enums import ConfidenceLevel


class StateTransitionEngine:
    """Analyze runtime state transitions and emit standardized risk evidence."""

    def __init__(
        self,
        state_provider: StateTransitionProvider | None = None,
        diff_builder: StateDiffBuilder | None = None,
    ) -> None:
        self._state_provider = state_provider
        self._diff_builder = diff_builder or StateDiffBuilder()

    async def analyze_transition(
        self,
        transition: RawStateTransition | Mapping[str, Any],
        *,
        transaction_hash: str | None = None,
        execution_report: RuntimeExecutionReport | None = None,
    ) -> RuntimeStateReport:
        normalized = _normalize_transition(transition, transaction_hash=transaction_hash)
        bundle = self._diff_builder.build(normalized)
        evidence = emit_state_evidence(
            transaction_hash=normalized.transaction_hash,
            bundle=bundle,
            execution_report=execution_report,
        )
        return RuntimeStateReport(
            transaction_hash=normalized.transaction_hash,
            storage_changes=bundle.storage_changes,
            balance_changes=bundle.balance_changes,
            allowance_changes=bundle.allowance_changes,
            ownership_changes=bundle.ownership_changes,
            supply_changes=bundle.supply_changes,
            mapped_state_events=bundle.mapped_state_events,
            risk_evidence=tuple(evidence),
            provider_name=normalized.provider_name,
        )

    async def analyze_hash(
        self,
        transaction_hash: str,
        *,
        chain_id: int = 1,
        block_number: int | None = None,
        execution_report: RuntimeExecutionReport | None = None,
    ) -> RuntimeStateReport:
        if self._state_provider is None:
            raise ValueError("state provider is required for hash-based analysis")
        transition = await self._state_provider.get_state_transition(
            transaction_hash,
            chain_id=chain_id,
            block_number=block_number,
        )
        return await self.analyze_transition(
            transition,
            execution_report=execution_report,
        )


def emit_state_evidence(
    *,
    transaction_hash: str,
    bundle: StateDiffBundle,
    execution_report: RuntimeExecutionReport | None = None,
) -> list[RiskEvidence]:
    """Convert state transition findings into standardized M7 RiskEvidence."""
    groups: list[list[RiskEvidence]] = [
        _storage_evidence(transaction_hash, bundle.storage_changes),
        _ownership_evidence(transaction_hash, bundle.ownership_changes),
        _allowance_evidence(transaction_hash, bundle.allowance_changes),
        _supply_evidence(transaction_hash, bundle.supply_changes),
    ]
    if execution_report is not None:
        groups.append(_execution_context_evidence(transaction_hash, execution_report))
    return merge_evidence(*groups)


def _storage_evidence(
    transaction_hash: str,
    storage_changes: tuple[StorageDiff, ...],
) -> list[RiskEvidence]:
    evidence: list[RiskEvidence] = []
    for change in storage_changes:
        if change.slot_kind != StorageSlotKind.IMPLEMENTATION:
            continue
        evidence.append(
            create_evidence(
                source=EvidenceSource.PROXY,
                category=EvidenceCategory.UPGRADEABILITY,
                signal="implementation_changed",
                severity=EvidenceSeverity.HIGH,
                score=Decimal("0.00"),
                confidence=ConfidenceLevel.HIGH,
                reason="Proxy implementation storage slot changed during execution",
                metadata={
                    EvidenceMetadataKey.SIGNAL.value: "implementation_changed",
                    EvidenceMetadataKey.REASON_ONLY.value: True,
                    "transaction_hash": transaction_hash,
                    "contract_address": change.contract_address,
                    "before_address": change.before_address,
                    "after_address": change.after_address,
                    "slot": change.slot,
                    "slot_kind": change.slot_kind.value,
                },
            )
        )
    return evidence


def _ownership_evidence(
    transaction_hash: str,
    ownership_changes: tuple[OwnershipChange, ...],
) -> list[RiskEvidence]:
    evidence: list[RiskEvidence] = []
    for change in ownership_changes:
        severity = EvidenceSeverity.HIGH if change.role == OwnershipRole.PROXY_ADMIN else EvidenceSeverity.MEDIUM
        evidence.append(
            create_evidence(
                source=EvidenceSource.GOVERNANCE,
                category=EvidenceCategory.AUTHORITY,
                signal="owner_changed",
                severity=severity,
                score=Decimal("0.00"),
                confidence=ConfidenceLevel.HIGH,
                reason=f"{change.role.value} changed during execution",
                metadata={
                    EvidenceMetadataKey.SIGNAL.value: "owner_changed",
                    EvidenceMetadataKey.REASON_ONLY.value: True,
                    "transaction_hash": transaction_hash,
                    "contract_address": change.contract_address,
                    "role": change.role.value,
                    "before_address": change.before_address,
                    "after_address": change.after_address,
                },
            )
        )
    return evidence


def _allowance_evidence(
    transaction_hash: str,
    allowance_changes: tuple[AllowanceChange, ...],
) -> list[RiskEvidence]:
    evidence: list[RiskEvidence] = []
    for change in allowance_changes:
        if change.kind != AllowanceChangeKind.UNLIMITED and not change.is_unlimited:
            continue
        evidence.append(
            create_evidence(
                source=EvidenceSource.CAPABILITY,
                category=EvidenceCategory.AUTHORITY,
                signal="unlimited_allowance_granted",
                severity=EvidenceSeverity.HIGH,
                score=Decimal("0.00"),
                confidence=ConfidenceLevel.HIGH,
                reason="Unlimited allowance granted during state transition",
                metadata={
                    EvidenceMetadataKey.SIGNAL.value: "unlimited_allowance_granted",
                    EvidenceMetadataKey.REASON_ONLY.value: True,
                    "transaction_hash": transaction_hash,
                    "token_address": change.token_address,
                    "owner_address": change.owner_address,
                    "spender_address": change.spender_address,
                },
            )
        )
    return evidence


def _supply_evidence(
    transaction_hash: str,
    supply_changes: tuple[SupplyChange, ...],
) -> list[RiskEvidence]:
    evidence: list[RiskEvidence] = []
    for change in supply_changes:
        if change.kind == SupplyChangeKind.INFLATION:
            evidence.append(
                create_evidence(
                    source=EvidenceSource.CAPABILITY,
                    category=EvidenceCategory.CAPABILITY,
                    signal="large_supply_inflation",
                    severity=EvidenceSeverity.HIGH,
                    score=Decimal("0.00"),
                    confidence=ConfidenceLevel.MEDIUM,
                    reason="Large token supply inflation detected during execution",
                    metadata={
                        EvidenceMetadataKey.SIGNAL.value: "large_supply_inflation",
                        EvidenceMetadataKey.REASON_ONLY.value: True,
                        "transaction_hash": transaction_hash,
                        "token_address": change.token_address,
                        "delta": str(change.delta),
                    },
                )
            )
        elif change.kind == SupplyChangeKind.MINT:
            evidence.append(
                create_evidence(
                    source=EvidenceSource.CAPABILITY,
                    category=EvidenceCategory.CAPABILITY,
                    signal="supply_mint",
                    severity=EvidenceSeverity.MEDIUM,
                    score=Decimal("0.00"),
                    confidence=ConfidenceLevel.MEDIUM,
                    reason="Token supply mint detected during execution",
                    metadata={
                        EvidenceMetadataKey.SIGNAL.value: "supply_mint",
                        EvidenceMetadataKey.REASON_ONLY.value: True,
                        "transaction_hash": transaction_hash,
                        "token_address": change.token_address,
                        "delta": str(change.delta),
                    },
                )
            )
        elif change.kind in {SupplyChangeKind.BURN, SupplyChangeKind.REDUCTION}:
            evidence.append(
                create_evidence(
                    source=EvidenceSource.CAPABILITY,
                    category=EvidenceCategory.CAPABILITY,
                    signal="supply_burn",
                    severity=EvidenceSeverity.LOW,
                    score=Decimal("0.00"),
                    confidence=ConfidenceLevel.MEDIUM,
                    reason="Token supply burn detected during execution",
                    metadata={
                        EvidenceMetadataKey.SIGNAL.value: "supply_burn",
                        EvidenceMetadataKey.REASON_ONLY.value: True,
                        "transaction_hash": transaction_hash,
                        "token_address": change.token_address,
                        "delta": str(change.delta),
                    },
                )
            )
    return evidence


def _execution_context_evidence(
    transaction_hash: str,
    execution_report: RuntimeExecutionReport,
) -> list[RiskEvidence]:
    if execution_report.revert_analysis.has_revert:
        return []
    return [
        create_evidence(
            source=EvidenceSource.CLASSIFICATION,
            category=EvidenceCategory.CLASSIFICATION,
            signal="state_transition_observed",
            severity=EvidenceSeverity.INFO,
            score=Decimal("0.00"),
            confidence=ConfidenceLevel.HIGH,
            reason="State transition correlated with runtime execution trace",
            metadata={
                EvidenceMetadataKey.SIGNAL.value: "state_transition_observed",
                EvidenceMetadataKey.REASON_ONLY.value: True,
                "transaction_hash": transaction_hash,
                "trace_provider": execution_report.provider_name,
                "call_count": len(execution_report.call_graph.nodes),
            },
        )
    ]


def _normalize_transition(
    transition: RawStateTransition | Mapping[str, Any],
    *,
    transaction_hash: str | None,
) -> RawStateTransition:
    if isinstance(transition, RawStateTransition):
        return transition
    return StateTransitionDecoder.decode(
        transition,
        transaction_hash=transaction_hash or str(transition.get("transaction_hash", "0x" + ("00" * 32))),
        provider_name=str(transition.get("provider_name", "decoded")),
        chain_id=transition.get("chain_id"),
    )
