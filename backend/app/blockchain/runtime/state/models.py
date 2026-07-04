"""State transition domain models (M9.3)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from app.blockchain.risk.models import RiskEvidence


class StorageSlotKind(StrEnum):
    """Semantic classification for storage slot changes."""

    IMPLEMENTATION = "implementation"
    PROXY_ADMIN = "proxy_admin"
    BEACON = "beacon"
    OWNER = "owner"
    ACCESS_CONTROL_ROLE = "access_control_role"
    TIMELOCK = "timelock"
    ARBITRARY = "arbitrary"


class BalanceAssetType(StrEnum):
    """Asset type for balance transitions."""

    NATIVE = "native"
    ERC20 = "erc20"
    ERC721 = "erc721"
    ERC1155 = "erc1155"


class AllowanceChangeKind(StrEnum):
    """Allowance transition type."""

    APPROVE = "approve"
    PERMIT = "permit"
    INCREASE = "increase"
    DECREASE = "decrease"
    REVOKE = "revoke"
    UNLIMITED = "unlimited"


class OwnershipRole(StrEnum):
    """Ownership or administrative role."""

    OWNER = "owner"
    PROXY_ADMIN = "proxy_admin"
    GOVERNOR = "governor"
    TREASURY = "treasury"
    MULTISIG = "multisig"


class SupplyChangeKind(StrEnum):
    """Token supply transition type."""

    MINT = "mint"
    BURN = "burn"
    INFLATION = "inflation"
    REDUCTION = "reduction"


class MappedEventKind(StrEnum):
    """Semantic mapped log event."""

    TRANSFER = "transfer"
    APPROVAL = "approval"
    OWNERSHIP_TRANSFERRED = "ownership_transferred"
    ROLE_GRANTED = "role_granted"
    ROLE_REVOKED = "role_revoked"


@dataclass(frozen=True, slots=True)
class RawStorageDiff:
    """Provider-normalized storage slot change."""

    contract_address: str
    slot: str
    before: str
    after: str


@dataclass(frozen=True, slots=True)
class RawBalanceDiff:
    """Provider-normalized account balance change."""

    asset_type: BalanceAssetType
    contract_address: str | None
    account_address: str
    before: int
    after: int
    token_id: int | None = None


@dataclass(frozen=True, slots=True)
class RawAllowanceDiff:
    """Provider-normalized allowance change."""

    token_address: str
    owner_address: str
    spender_address: str
    before: int
    after: int


@dataclass(frozen=True, slots=True)
class RawSupplyDiff:
    """Provider-normalized total supply change."""

    token_address: str
    before: int
    after: int


@dataclass(frozen=True, slots=True)
class RawStateLog:
    """Provider-normalized execution log."""

    contract_address: str
    topics: tuple[str, ...]
    data: bytes


@dataclass(frozen=True, slots=True)
class RawStateTransition:
    """Normalized pre/post state transition payload."""

    transaction_hash: str
    block_number: int | None
    storage_diffs: tuple[RawStorageDiff, ...]
    balance_diffs: tuple[RawBalanceDiff, ...]
    allowance_diffs: tuple[RawAllowanceDiff, ...]
    supply_diffs: tuple[RawSupplyDiff, ...]
    logs: tuple[RawStateLog, ...]
    provider_name: str
    chain_id: int | None = None


@dataclass(frozen=True, slots=True)
class StorageDiff:
    """Semantic storage slot change."""

    contract_address: str
    slot: str
    slot_kind: StorageSlotKind
    before: str
    after: str
    before_address: str | None = None
    after_address: str | None = None


@dataclass(frozen=True, slots=True)
class BalanceChange:
    """Semantic balance transition."""

    asset_type: BalanceAssetType
    contract_address: str | None
    account_address: str
    before: int
    after: int
    delta: int
    token_id: int | None = None
    counterparty: str | None = None


@dataclass(frozen=True, slots=True)
class AllowanceChange:
    """Semantic allowance transition."""

    kind: AllowanceChangeKind
    token_address: str
    owner_address: str
    spender_address: str
    before: int
    after: int
    is_unlimited: bool


@dataclass(frozen=True, slots=True)
class OwnershipChange:
    """Before/after ownership or admin transition."""

    role: OwnershipRole
    contract_address: str
    before_address: str | None
    after_address: str | None


@dataclass(frozen=True, slots=True)
class SupplyChange:
    """Token supply transition."""

    kind: SupplyChangeKind
    token_address: str
    before: int
    after: int
    delta: int


@dataclass(frozen=True, slots=True)
class MappedStateEvent:
    """Semantic state event mapped from execution logs."""

    event_kind: MappedEventKind
    contract_address: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class RuntimeStateReport:
    """Runtime state transition intelligence output."""

    transaction_hash: str
    storage_changes: tuple[StorageDiff, ...]
    balance_changes: tuple[BalanceChange, ...]
    allowance_changes: tuple[AllowanceChange, ...]
    ownership_changes: tuple[OwnershipChange, ...]
    supply_changes: tuple[SupplyChange, ...]
    mapped_state_events: tuple[MappedStateEvent, ...]
    risk_evidence: tuple[RiskEvidence, ...]
    provider_name: str
