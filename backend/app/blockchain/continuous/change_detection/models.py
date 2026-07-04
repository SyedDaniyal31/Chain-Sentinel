"""Change detection domain models (M10.2)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any

from app.models.enums import ConfidenceLevel


class ChangeType(StrEnum):
    """Structured protocol change categories."""

    IMPLEMENTATION_CHANGED = "implementation_changed"
    OWNER_CHANGED = "owner_changed"
    PROXY_ADMIN_CHANGED = "proxy_admin_changed"
    GOVERNANCE_CHANGED = "governance_changed"
    LIQUIDITY_CHANGED = "liquidity_changed"
    TREASURY_CHANGED = "treasury_changed"
    BYTECODE_CHANGED = "bytecode_changed"
    DEPENDENCY_CHANGED = "dependency_changed"
    RUNTIME_FINGERPRINT_CHANGED = "runtime_fingerprint_changed"


class ChangeSeverity(StrEnum):
    """Impact severity for detected protocol changes."""

    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass(frozen=True, slots=True)
class ContractSnapshot:
    """Immutable snapshot state for a single protocol contract."""

    address: str
    proxy_implementation: str | None = None
    owner: str | None = None
    proxy_admin: str | None = None
    timelock: str | None = None
    governor: str | None = None
    treasury: str | None = None
    bytecode_hash: str | None = None
    abi_hash: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ProtocolSnapshot:
    """Immutable protocol-wide snapshot for change detection."""

    snapshot_id: str
    watch_id: str
    chain_id: int
    root_address: str
    captured_at: datetime
    contracts: tuple[ContractSnapshot, ...]
    dependency_fingerprint: str
    liquidity_fingerprint: str
    runtime_fingerprint: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ChangeEvent:
    """Structured change detected between baseline and current snapshots."""

    event_id: str
    change_type: ChangeType
    severity: ChangeSeverity
    before: str | None
    after: str | None
    affected_contracts: tuple[str, ...]
    timestamp: datetime
    confidence: ConfidenceLevel
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ChangeDetectionResult:
    """Output of a baseline vs current snapshot comparison."""

    watch_id: str
    baseline_snapshot_id: str
    current_snapshot_id: str
    detected_at: datetime
    changes: tuple[ChangeEvent, ...]
    unchanged: bool
