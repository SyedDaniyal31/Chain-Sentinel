"""Protocol discovery domain models (M8.1)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class ProtocolRole(StrEnum):
    """Functional role of a contract within a discovered protocol."""

    ROOT = "root"
    PROXY = "proxy"
    IMPLEMENTATION = "implementation"
    GOVERNOR = "governor"
    TIMELOCK = "timelock"
    ROUTER = "router"
    FACTORY = "factory"
    POOL = "pool"
    VAULT = "vault"
    STRATEGY = "strategy"
    TOKEN = "token"
    TREASURY = "treasury"
    ORACLE = "oracle"
    BRIDGE = "bridge"
    MESSENGER = "messenger"
    UNKNOWN = "unknown"


class ProtocolRelationshipType(StrEnum):
    """Typed edge between discovered protocol contracts."""

    PROXY_TO_IMPLEMENTATION = "PROXY_TO_IMPLEMENTATION"
    GOVERNOR_TO_TIMELOCK = "GOVERNOR_TO_TIMELOCK"
    ROUTER_TO_FACTORY = "ROUTER_TO_FACTORY"
    FACTORY_TO_POOL = "FACTORY_TO_POOL"
    VAULT_TO_STRATEGY = "VAULT_TO_STRATEGY"
    TOKEN_TO_TREASURY = "TOKEN_TO_TREASURY"
    BRIDGE_TO_MESSENGER = "BRIDGE_TO_MESSENGER"


@dataclass(frozen=True, slots=True)
class ProtocolContract:
    """Single contract node belonging to a protocol discovery graph."""

    address: str
    role: ProtocolRole
    confidence: int
    detection_source: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ProtocolRelationship:
    """Directed relationship between two discovered protocol contracts."""

    source_address: str
    target_address: str
    relationship_type: ProtocolRelationshipType
    confidence: int
    detection_source: str


@dataclass(frozen=True, slots=True)
class ProtocolDiscoveryResult:
    """Aggregated protocol discovery output for a root contract."""

    root_address: str
    chain_id: int
    protocol_name: str
    protocol_family: str
    contracts: tuple[ProtocolContract, ...]
    relationships: tuple[ProtocolRelationship, ...]
    confidence: int
    detection_sources: tuple[str, ...]
