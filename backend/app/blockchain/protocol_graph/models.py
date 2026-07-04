"""Protocol dependency graph domain models (M8.2)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from app.blockchain.protocol_scan.models import ProtocolRole


class GraphEdgeType(StrEnum):
    """Directed protocol dependency edge types for scan execution planning."""

    PROXY_TO_IMPLEMENTATION = "PROXY_TO_IMPLEMENTATION"
    ADMIN_TO_PROXY = "ADMIN_TO_PROXY"
    GOVERNOR_TO_TIMELOCK = "GOVERNOR_TO_TIMELOCK"
    ROUTER_TO_FACTORY = "ROUTER_TO_FACTORY"
    FACTORY_TO_POOL = "FACTORY_TO_POOL"
    VAULT_TO_STRATEGY = "VAULT_TO_STRATEGY"
    TOKEN_TO_TREASURY = "TOKEN_TO_TREASURY"
    BRIDGE_TO_MESSENGER = "BRIDGE_TO_MESSENGER"
    ORACLE_TO_PROTOCOL = "ORACLE_TO_PROTOCOL"
    DEPENDS_ON = "DEPENDS_ON"


@dataclass(frozen=True, slots=True)
class ProtocolNode:
    """Node in a protocol dependency graph."""

    address: str
    role: ProtocolRole
    protocol_name: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ProtocolEdge:
    """Directed edge in a protocol dependency graph."""

    source: str
    target: str
    relationship_type: GraphEdgeType
    confidence: int


@dataclass(frozen=True, slots=True)
class ProtocolGraph:
    """Directed protocol dependency graph used as a scan execution plan."""

    nodes: tuple[ProtocolNode, ...]
    edges: tuple[ProtocolEdge, ...]
    root_node: str
    adjacency_map: dict[str, tuple[str, ...]]


@dataclass(frozen=True, slots=True)
class GraphValidationIssue:
    """Single graph integrity issue."""

    code: str
    message: str
    address: str | None = None


@dataclass(frozen=True, slots=True)
class GraphValidationReport:
    """Validation output for a protocol dependency graph."""

    is_valid: bool
    issues: tuple[GraphValidationIssue, ...]
    disconnected_nodes: tuple[str, ...]
    orphan_nodes: tuple[str, ...]
    cycles: tuple[tuple[str, ...], ...]
