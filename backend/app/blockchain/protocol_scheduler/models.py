"""Protocol scan scheduler domain models (M8.3)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any

from app.schemas.scan_result import ContractAnalysisData


class NodeScanStatus(StrEnum):
    """Lifecycle status for a protocol graph node scan."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass(frozen=True, slots=True)
class ExecutionBatch:
    """Parallel execution batch of node addresses."""

    batch_index: int
    addresses: tuple[str, ...]


@dataclass(slots=True)
class NodeScanResult:
    """Scan outcome for a single protocol graph node."""

    address: str
    status: NodeScanStatus
    analysis: ContractAnalysisData | None = None
    error: str | None = None
    duration_ms: float = 0.0
    retry_count: int = 0
    started_at: datetime | None = None
    completed_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class ScanTimingInfo:
    """Wall-clock timing for a protocol scan run."""

    started_at: datetime
    completed_at: datetime
    total_duration_ms: float


@dataclass(frozen=True, slots=True)
class ProtocolScanMetrics:
    """Execution metrics collected during a protocol scan."""

    nodes_scanned: int
    parallel_batches_executed: int
    total_duration_ms: float
    average_node_duration_ms: float
    retry_count: int


@dataclass(frozen=True, slots=True)
class ProtocolScanResult:
    """Aggregated output of a protocol-wide scan execution."""

    execution_order: tuple[str, ...]
    completed_nodes: tuple[str, ...]
    failed_nodes: tuple[str, ...]
    aggregated_evidence: dict[str, Any]
    metrics: ProtocolScanMetrics
    timing: ScanTimingInfo
    node_results: tuple[NodeScanResult, ...] = field(default_factory=tuple)
    execution_batches: tuple[ExecutionBatch, ...] = field(default_factory=tuple)


def utc_now() -> datetime:
    """Return the current UTC timestamp."""
    return datetime.now(timezone.utc)
