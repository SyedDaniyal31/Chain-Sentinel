"""Threat surface domain models (M6.4)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class DependencyCategory(StrEnum):
    """External dependency classification."""

    BRIDGE = "bridge"
    ORACLE = "oracle"
    DEX = "dex"
    VAULT = "vault"
    PROXY = "proxy"
    GOVERNANCE = "governance"
    LENDING = "lending"


class TrustBoundaryKind(StrEnum):
    """Trust boundary categories for attack surface analysis."""

    ORACLE = "oracle"
    BRIDGE = "bridge"
    VAULT = "vault"
    ROUTER = "router"
    TREASURY = "treasury"
    GOVERNOR = "governor"
    OWNER = "owner"
    TIMELOCK = "timelock"
    MULTISIG = "multisig"
    UPGRADEABLE_PROXY = "upgradeable_proxy"


class PrivilegedEntityType(StrEnum):
    """Privileged entity roles with elevated control."""

    OWNER = "owner"
    PROXY_ADMIN = "proxy_admin"
    GOVERNOR = "governor"
    DAO = "dao"
    TIMELOCK = "timelock"
    SAFE = "safe"
    MULTISIG = "multisig"
    BRIDGE_RELAYER = "bridge_relayer"
    ORACLE_ADMIN = "oracle_admin"
    CAPABILITY_CONTROLLER = "capability_controller"


@dataclass(frozen=True, slots=True)
class ExternalDependency:
    category: DependencyCategory
    name: str
    role: str
    confidence: int
    detection_source: str
    address: str | None = None


@dataclass(frozen=True, slots=True)
class TrustBoundary:
    boundary_type: TrustBoundaryKind
    label: str
    confidence: int
    detection_source: str
    address: str | None = None


@dataclass(frozen=True, slots=True)
class PrivilegedEntity:
    entity_type: PrivilegedEntityType
    label: str
    confidence: int
    detection_source: str
    address: str | None = None


@dataclass(frozen=True, slots=True)
class AttackPath:
    name: str
    steps: tuple[str, ...]
    confidence: int
    detection_source: str


@dataclass(frozen=True, slots=True)
class CriticalAsset:
    asset_type: str
    label: str
    confidence: int
    address: str | None = None


@dataclass(frozen=True, slots=True)
class DependencyGraphNode:
    id: str
    label: str
    node_type: str
    address: str | None = None


@dataclass(frozen=True, slots=True)
class DependencyGraphEdge:
    source: str
    target: str
    relationship: str
    confidence: int


@dataclass
class DependencyGraph:
    nodes: list[DependencyGraphNode] = field(default_factory=list)
    edges: list[DependencyGraphEdge] = field(default_factory=list)


@dataclass
class ThreatSurfaceResult:
    """Aggregated threat surface analysis output."""

    external_dependencies: list[ExternalDependency] = field(default_factory=list)
    trust_boundaries: list[TrustBoundary] = field(default_factory=list)
    privileged_entities: list[PrivilegedEntity] = field(default_factory=list)
    attack_paths: list[AttackPath] = field(default_factory=list)
    dependency_graph: DependencyGraph = field(default_factory=DependencyGraph)
    critical_assets: list[CriticalAsset] = field(default_factory=list)


@dataclass
class ThreatSurfaceContext:
    """Inputs consumed by M6.4 threat surface analysis."""

    target_address: str
    protocol_family: str = "unknown"
    proxy_type: str = "none"
    is_upgradeable: bool = False
    is_verified: bool = False
    implementation_address: str | None = None
    admin_address: str | None = None
    owner_address: str | None = None
    governance_type: str | None = None
    upgrade_authority: str | None = None
    governance_ownership_address: str | None = None
    governance_ownership_renounced: bool = False
    has_timelock: bool = False
    treasury_is_multisig: bool = False
    dexes: list[dict] = field(default_factory=list)
    lending: list[dict] = field(default_factory=list)
    oracles: list[dict] = field(default_factory=list)
    bridges: list[dict] = field(default_factory=list)
    vaults: list[dict] = field(default_factory=list)
    governance_protocols: list[dict] = field(default_factory=list)
    relationships: list[dict] = field(default_factory=list)
    liquidity_has_liquidity: bool = False
    liquidity_primary_dex: str | None = None
    liquidity_pair_address: str | None = None
    liquidity_usd: str | None = None
    wallet_creator: str | None = None
    wallet_deployer: str | None = None
    wallet_owner: str | None = None
    wallet_treasury: str | None = None
    capability_controllers: list[tuple[str, str]] = field(default_factory=list)
    mint_capability: bool = False
    pause_capability: bool = False
    honeypot_is_suspected: bool = False
    honeypot_is_confirmed: bool = False
