"""Runtime transaction classification (M9.1)."""

from __future__ import annotations

from app.blockchain.runtime.transaction.models import (
    ApprovalFinding,
    DecodedFunction,
    PrivilegedAction,
    TokenTransfer,
    TransactionCategory,
    TransactionFormat,
    TransactionMetadata,
)
from app.blockchain.runtime.transaction.selector_registry import SelectorRegistry


class TransactionClassifier:
    """Classify transactions into semantic runtime categories."""

    def __init__(self, selector_registry: SelectorRegistry | None = None) -> None:
        self._selector_registry = selector_registry or SelectorRegistry()

    def classify(
        self,
        metadata: TransactionMetadata,
        decoded_function: DecodedFunction | None,
        transfers: tuple[TokenTransfer, ...],
        approvals: tuple[ApprovalFinding, ...],
        privileged_actions: tuple[PrivilegedAction, ...],
    ) -> TransactionCategory:
        if metadata.transaction_format == TransactionFormat.CONTRACT_CREATION:
            return TransactionCategory.DEPLOYMENT

        if approvals:
            return TransactionCategory.APPROVAL

        if privileged_actions:
            operation = privileged_actions[0].operation
            if operation.value in {"upgradeTo", "upgradeToAndCall", "setImplementation"}:
                return TransactionCategory.UPGRADE
            if operation.value in {"mint"}:
                return TransactionCategory.MINT
            if operation.value in {"burn"}:
                return TransactionCategory.BURN
            return TransactionCategory.GOVERNANCE

        if decoded_function is not None:
            entry = self._selector_registry.lookup(decoded_function.selector)
            if entry and entry.category:
                return entry.category
            name = decoded_function.function_name.lower()
            if "swap" in name:
                return TransactionCategory.SWAP
            if "liquidity" in name:
                return TransactionCategory.LIQUIDITY
            if "flash" in name:
                return TransactionCategory.FLASH_LOAN
            if "bridge" in name or "message" in name:
                return TransactionCategory.BRIDGE
            if name in {"propose", "castvote", "execute", "schedule"}:
                return TransactionCategory.GOVERNANCE

        if transfers and metadata.value_wei > 0 and decoded_function is None:
            return TransactionCategory.TRANSFER

        if transfers:
            return TransactionCategory.TRANSFER

        return TransactionCategory.UNKNOWN
