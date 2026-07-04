"""Transaction intelligence domain models (M9.1)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from app.blockchain.risk.models import RiskEvidence


class TransactionFormat(StrEnum):
    """Normalized Ethereum transaction envelope type."""

    LEGACY = "legacy"
    EIP1559 = "eip1559"
    CONTRACT_CREATION = "contract_creation"


class TransactionCategory(StrEnum):
    """High-level runtime transaction classification."""

    SWAP = "swap"
    LIQUIDITY = "liquidity"
    BRIDGE = "bridge"
    GOVERNANCE = "governance"
    UPGRADE = "upgrade"
    TREASURY = "treasury"
    APPROVAL = "approval"
    FLASH_LOAN = "flash_loan"
    DEPLOYMENT = "deployment"
    MINT = "mint"
    BURN = "burn"
    TRANSFER = "transfer"
    UNKNOWN = "unknown"


class TokenStandard(StrEnum):
    """Token transfer standard detected from calldata heuristics."""

    NATIVE = "native"
    ERC20 = "erc20"
    ERC721 = "erc721"
    ERC1155 = "erc1155"


class ApprovalKind(StrEnum):
    """Approval operation type."""

    APPROVE = "approve"
    PERMIT = "permit"
    SET_APPROVAL_FOR_ALL = "setApprovalForAll"


class PrivilegedOperation(StrEnum):
    """Privileged administrative operation."""

    UPGRADE_TO = "upgradeTo"
    UPGRADE_TO_AND_CALL = "upgradeToAndCall"
    SET_IMPLEMENTATION = "setImplementation"
    PAUSE = "pause"
    UNPAUSE = "unpause"
    MINT = "mint"
    BURN = "burn"
    TRANSFER_OWNERSHIP = "transferOwnership"
    GRANT_ROLE = "grantRole"
    REVOKE_ROLE = "revokeRole"


@dataclass(frozen=True, slots=True)
class TransactionMetadata:
    """Normalized transaction envelope metadata."""

    transaction_hash: str
    chain_id: int | None
    from_address: str
    to_address: str | None
    value_wei: int
    nonce: int
    gas: int
    gas_price_wei: int | None
    max_fee_per_gas_wei: int | None
    max_priority_fee_per_gas_wei: int | None
    transaction_format: TransactionFormat
    block_number: int | None = None
    input_size: int = 0


@dataclass(frozen=True, slots=True)
class DecodedArgument:
    """Single decoded function argument."""

    name: str
    value: Any
    solidity_type: str


@dataclass(frozen=True, slots=True)
class DecodedFunction:
    """Decoded contract call metadata."""

    selector: str
    function_name: str
    signature: str | None
    arguments: tuple[DecodedArgument, ...]
    decode_source: str
    raw_calldata: bytes


@dataclass(frozen=True, slots=True)
class TokenTransfer:
    """Detected value or token movement."""

    standard: TokenStandard
    from_address: str
    to_address: str
    amount: int | None
    token_address: str | None
    token_id: int | None = None
    operator: str | None = None


@dataclass(frozen=True, slots=True)
class ApprovalFinding:
    """Detected approval or allowance operation."""

    kind: ApprovalKind
    token_address: str
    owner_address: str
    spender_address: str
    amount: int | None
    is_unlimited: bool
    is_infinite_allowance: bool
    spender_risk_indicators: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class PrivilegedAction:
    """Detected privileged administrative action."""

    operation: PrivilegedOperation
    contract_address: str
    actor_address: str
    target_address: str | None = None
    role: str | None = None
    amount: int | None = None
    is_large_transfer: bool = False


@dataclass(frozen=True, slots=True)
class TransactionIntelligence:
    """Runtime transaction intelligence output."""

    metadata: TransactionMetadata
    decoded_function: DecodedFunction | None
    token_transfers: tuple[TokenTransfer, ...]
    approvals: tuple[ApprovalFinding, ...]
    privileged_actions: tuple[PrivilegedAction, ...]
    category: TransactionCategory
    risk_evidence: tuple[RiskEvidence, ...]
