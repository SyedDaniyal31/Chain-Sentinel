"""Cross-protocol relationship domain models (M6.3)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class RelationshipType(StrEnum):
    """Directed semantic relationship between architecture nodes."""

    USES = "USES"
    INTEGRATES = "INTEGRATES"
    DEPENDS_ON = "DEPENDS_ON"
    GOVERNED_BY = "GOVERNED_BY"
    UPGRADEABLE_BY = "UPGRADEABLE_BY"
    TRADES_ON = "TRADES_ON"
    PRICES_WITH = "PRICES_WITH"
    BRIDGES_WITH = "BRIDGES_WITH"
    SECURED_BY = "SECURED_BY"
    OWNED_BY = "OWNED_BY"
    CREATED_BY = "CREATED_BY"
    DEPLOYS = "DEPLOYS"


class ArchitectureNodeType(StrEnum):
    """Node classification for architecture graphs."""

    CONTRACT = "contract"
    PROTOCOL = "protocol"
    WALLET = "wallet"
    DEX = "dex"
    ORACLE = "oracle"
    BRIDGE = "bridge"
    VAULT = "vault"
    GOVERNANCE = "governance"
    LIQUIDITY = "liquidity"
    IMPLEMENTATION = "implementation"


@dataclass(frozen=True, slots=True)
class ProtocolRelationshipCandidate:
    """Raw relationship edge before engine normalization."""

    source_id: str
    source_label: str
    source_type: ArchitectureNodeType
    target_id: str
    target_label: str
    target_type: ArchitectureNodeType
    relationship_type: RelationshipType
    confidence: int
    detection_source: str
    target_address: str | None = None


@dataclass(frozen=True, slots=True)
class ProtocolRelationship:
    """Normalized relationship edge exposed via API."""

    source: str
    target: str
    relationship_type: RelationshipType
    confidence: int
    detection_source: str


@dataclass(frozen=True, slots=True)
class ArchitectureGraphNode:
    """Graph node compatible with future visualization libraries."""

    id: str
    label: str
    node_type: str
    address: str | None = None


@dataclass(frozen=True, slots=True)
class ArchitectureGraphEdge:
    """Graph edge with relationship metadata."""

    source: str
    target: str
    relationship: str
    confidence: int
    detection_source: str


@dataclass
class ArchitectureGraph:
    """Graph-ready architecture model."""

    nodes: list[ArchitectureGraphNode] = field(default_factory=list)
    edges: list[ArchitectureGraphEdge] = field(default_factory=list)


@dataclass
class ArchitectureSummary:
    """Data-driven architecture summary derived from detector outputs."""

    application_type: str = "unknown"
    protocol_stack: list[str] = field(default_factory=list)
    oracle: str | None = None
    liquidity: str | None = None
    bridge: str | None = None
    governance: str | None = None
    upgradeability: str | None = None
    ownership: str | None = None


@dataclass
class RelationshipAnalysisContext:
    """Inputs consumed by M6.3 relationship analysis."""

    target_address: str
    protocol_family: str = "unknown"
    protocol_name: str = "unknown"
    protocol_type: str = "unknown"
    proxy_type: str = "none"
    is_verified: bool = False
    is_upgradeable: bool = False
    implementation_address: str | None = None
    admin_address: str | None = None
    owner_address: str | None = None
    governance_type: str | None = None
    upgrade_authority: str | None = None
    governance_ownership_address: str | None = None
    governance_ownership_renounced: bool = False
    has_timelock: bool = False
    dexes: list[dict] = field(default_factory=list)
    lending: list[dict] = field(default_factory=list)
    oracles: list[dict] = field(default_factory=list)
    bridges: list[dict] = field(default_factory=list)
    vaults: list[dict] = field(default_factory=list)
    nfts: list[dict] = field(default_factory=list)
    governance_protocols: list[dict] = field(default_factory=list)
    integrations: list[str] = field(default_factory=list)
    standards: list[str] = field(default_factory=list)
    liquidity_has_liquidity: bool = False
    liquidity_primary_dex: str | None = None
    liquidity_pair_address: str | None = None
    wallet_creator: str | None = None
    wallet_deployer: str | None = None
    wallet_owner: str | None = None
    wallet_treasury: str | None = None
    wallet_proxy_admin: str | None = None
    capability_controllers: list[tuple[str, str]] = field(default_factory=list)
    honeypot_is_suspected: bool = False
