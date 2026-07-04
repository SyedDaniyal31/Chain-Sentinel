"""Transaction intelligence orchestrator and evidence emission (M9.1)."""

from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal
from typing import Any, Protocol

from app.blockchain.contract_source_provider import ContractSourceProvider, NullContractSourceProvider
from app.blockchain.risk.evidence import create_evidence, merge_evidence
from app.blockchain.risk.evidence_types import (
    EvidenceCategory,
    EvidenceMetadataKey,
    EvidenceSeverity,
    EvidenceSource,
)
from app.blockchain.risk.models import RiskEvidence
from app.blockchain.runtime.transaction.abi_decoder import ABIDecoder
from app.blockchain.runtime.transaction.approval_analyzer import ApprovalAnalyzer
from app.blockchain.runtime.transaction.decoder import TransactionDecoder
from app.blockchain.runtime.transaction.models import (
    ApprovalFinding,
    PrivilegedAction,
    TransactionCategory,
    TransactionIntelligence,
    TransactionMetadata,
)
from app.blockchain.runtime.transaction.privilege_analyzer import PrivilegeAnalyzer
from app.blockchain.runtime.transaction.selector_registry import SelectorRegistry
from app.blockchain.runtime.transaction.transaction_classifier import TransactionClassifier
from app.blockchain.runtime.transaction.transfer_analyzer import TransferAnalyzer
from app.models.enums import ConfidenceLevel


class TransactionProvider(Protocol):
    """Optional provider for resolving transactions by hash."""

    async def get_transaction(self, transaction_hash: str) -> Mapping[str, Any]:
        """Fetch a raw transaction object by hash."""


class TransactionIntelligenceEngine:
    """Analyze Ethereum transactions and emit standardized risk evidence."""

    def __init__(
        self,
        source_provider: ContractSourceProvider | None = None,
        selector_registry: SelectorRegistry | None = None,
        transaction_provider: TransactionProvider | None = None,
    ) -> None:
        registry = selector_registry or SelectorRegistry()
        provider = source_provider or NullContractSourceProvider()
        self._decoder = TransactionDecoder()
        self._abi_decoder = ABIDecoder(provider, registry)
        self._classifier = TransactionClassifier(registry)
        self._transaction_provider = transaction_provider

    async def analyze_transaction(
        self,
        raw_transaction: Mapping[str, Any],
        *,
        chain_id: int | None = None,
    ) -> TransactionIntelligence:
        metadata = self._decoder.decode(raw_transaction)
        calldata = self._decoder.extract_calldata(raw_transaction)
        effective_chain_id = chain_id if chain_id is not None else metadata.chain_id or 1

        decoded_function = await self._abi_decoder.decode(
            metadata.to_address,
            calldata,
            chain_id=effective_chain_id,
        )
        transfers = TransferAnalyzer.analyze(metadata, decoded_function)
        approvals = ApprovalAnalyzer.analyze(metadata, decoded_function)
        privileged_actions = PrivilegeAnalyzer.analyze(metadata, decoded_function)
        category = self._classifier.classify(
            metadata,
            decoded_function,
            transfers,
            approvals,
            privileged_actions,
        )
        evidence = emit_transaction_evidence(
            metadata=metadata,
            category=category,
            approvals=approvals,
            privileged_actions=privileged_actions,
            decoded_function=decoded_function,
        )

        return TransactionIntelligence(
            metadata=metadata,
            decoded_function=decoded_function,
            token_transfers=transfers,
            approvals=approvals,
            privileged_actions=privileged_actions,
            category=category,
            risk_evidence=tuple(evidence),
        )

    async def analyze_hash(
        self,
        transaction_hash: str,
        *,
        chain_id: int = 1,
    ) -> TransactionIntelligence:
        if self._transaction_provider is None:
            raise ValueError("transaction provider is required for hash-based analysis")
        raw_transaction = await self._transaction_provider.get_transaction(transaction_hash)
        return await self.analyze_transaction(raw_transaction, chain_id=chain_id)


def emit_transaction_evidence(
    *,
    metadata: TransactionMetadata,
    category: TransactionCategory,
    approvals: tuple[ApprovalFinding, ...],
    privileged_actions: tuple[PrivilegedAction, ...],
    decoded_function: Any,
) -> list[RiskEvidence]:
    """Convert runtime findings into standardized M7 RiskEvidence objects."""
    groups: list[list[RiskEvidence]] = []

    groups.append(_classification_evidence(metadata, category, decoded_function))
    groups.append(_approval_evidence(metadata, approvals))
    groups.append(_privilege_evidence(metadata, privileged_actions))

    return merge_evidence(*groups)


def _classification_evidence(
    metadata: TransactionMetadata,
    category: TransactionCategory,
    decoded_function: Any,
) -> list[RiskEvidence]:
    function_name = decoded_function.function_name if decoded_function else "none"
    return [
        create_evidence(
            source=EvidenceSource.CLASSIFICATION,
            category=EvidenceCategory.CLASSIFICATION,
            signal=f"transaction_{category.value}",
            severity=EvidenceSeverity.INFO,
            score=Decimal("0.00"),
            confidence=ConfidenceLevel.HIGH,
            reason=f"Transaction classified as {category.value}",
            metadata={
                EvidenceMetadataKey.SIGNAL.value: f"transaction_{category.value}",
                EvidenceMetadataKey.REASON_ONLY.value: True,
                "transaction_hash": metadata.transaction_hash,
                "function_name": function_name,
            },
        )
    ]


def _approval_evidence(
    metadata: TransactionMetadata,
    approvals: tuple[ApprovalFinding, ...],
) -> list[RiskEvidence]:
    evidence: list[RiskEvidence] = []
    for approval in approvals:
        if approval.is_unlimited:
            evidence.append(
                create_evidence(
                    source=EvidenceSource.CAPABILITY,
                    category=EvidenceCategory.AUTHORITY,
                    signal="unlimited_approval",
                    severity=EvidenceSeverity.HIGH,
                    score=Decimal("0.00"),
                    confidence=ConfidenceLevel.HIGH,
                    reason="Unlimited token approval granted to external spender",
                    metadata={
                        EvidenceMetadataKey.SIGNAL.value: "unlimited_approval",
                        EvidenceMetadataKey.REASON_ONLY.value: True,
                        "transaction_hash": metadata.transaction_hash,
                        "token_address": approval.token_address,
                        "spender_address": approval.spender_address,
                        "approval_kind": approval.kind.value,
                        "spender_risk_indicators": list(approval.spender_risk_indicators),
                    },
                )
            )
        else:
            evidence.append(
                create_evidence(
                    source=EvidenceSource.CAPABILITY,
                    category=EvidenceCategory.AUTHORITY,
                    signal="token_approval",
                    severity=EvidenceSeverity.LOW,
                    score=Decimal("0.00"),
                    confidence=ConfidenceLevel.MEDIUM,
                    reason="Token approval granted to external spender",
                    metadata={
                        EvidenceMetadataKey.SIGNAL.value: "token_approval",
                        EvidenceMetadataKey.REASON_ONLY.value: True,
                        "transaction_hash": metadata.transaction_hash,
                        "token_address": approval.token_address,
                        "spender_address": approval.spender_address,
                        "amount": str(approval.amount),
                    },
                )
            )
    return evidence


def _privilege_evidence(
    metadata: TransactionMetadata,
    privileged_actions: tuple[PrivilegedAction, ...],
) -> list[RiskEvidence]:
    evidence: list[RiskEvidence] = []
    for action in privileged_actions:
        if action.operation.value in {"upgradeTo", "upgradeToAndCall", "setImplementation"}:
            evidence.append(
                create_evidence(
                    source=EvidenceSource.PROXY,
                    category=EvidenceCategory.UPGRADEABILITY,
                    signal="upgrade_executed",
                    severity=EvidenceSeverity.HIGH,
                    score=Decimal("0.00"),
                    confidence=ConfidenceLevel.HIGH,
                    reason="Contract upgrade executed on-chain",
                    metadata={
                        EvidenceMetadataKey.SIGNAL.value: "upgrade_executed",
                        EvidenceMetadataKey.REASON_ONLY.value: True,
                        "transaction_hash": metadata.transaction_hash,
                        "contract_address": action.contract_address,
                        "target_address": action.target_address,
                        "operation": action.operation.value,
                    },
                )
            )
        elif action.operation.value in {"grantRole", "revokeRole", "transferOwnership"}:
            evidence.append(
                create_evidence(
                    source=EvidenceSource.GOVERNANCE,
                    category=EvidenceCategory.AUTHORITY,
                    signal=f"privileged_{action.operation.value}",
                    severity=EvidenceSeverity.MEDIUM,
                    score=Decimal("0.00"),
                    confidence=ConfidenceLevel.MEDIUM,
                    reason=f"Privileged governance operation executed: {action.operation.value}",
                    metadata={
                        EvidenceMetadataKey.SIGNAL.value: f"privileged_{action.operation.value}",
                        EvidenceMetadataKey.REASON_ONLY.value: True,
                        "transaction_hash": metadata.transaction_hash,
                        "contract_address": action.contract_address,
                        "target_address": action.target_address,
                        "role": action.role,
                    },
                )
            )
        elif action.operation.value in {"mint", "burn", "pause", "unpause"}:
            evidence.append(
                create_evidence(
                    source=EvidenceSource.CAPABILITY,
                    category=EvidenceCategory.CAPABILITY,
                    signal=f"privileged_{action.operation.value}",
                    severity=EvidenceSeverity.MEDIUM,
                    score=Decimal("0.00"),
                    confidence=ConfidenceLevel.MEDIUM,
                    reason=f"Privileged capability operation executed: {action.operation.value}",
                    metadata={
                        EvidenceMetadataKey.SIGNAL.value: f"privileged_{action.operation.value}",
                        EvidenceMetadataKey.REASON_ONLY.value: True,
                        "transaction_hash": metadata.transaction_hash,
                        "contract_address": action.contract_address,
                        "amount": str(action.amount) if action.amount is not None else None,
                    },
                )
            )

        if action.is_large_transfer:
            evidence.append(
                create_evidence(
                    source=EvidenceSource.GOVERNANCE,
                    category=EvidenceCategory.AUTHORITY,
                    signal="large_privileged_transfer",
                    severity=EvidenceSeverity.HIGH,
                    score=Decimal("0.00"),
                    confidence=ConfidenceLevel.MEDIUM,
                    reason="Large privileged transfer or mint detected in runtime transaction",
                    metadata={
                        EvidenceMetadataKey.SIGNAL.value: "large_privileged_transfer",
                        EvidenceMetadataKey.REASON_ONLY.value: True,
                        "transaction_hash": metadata.transaction_hash,
                        "contract_address": action.contract_address,
                        "amount": str(action.amount) if action.amount is not None else None,
                        "operation": action.operation.value,
                    },
                )
            )
    return evidence
