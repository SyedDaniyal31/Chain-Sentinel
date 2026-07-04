"""Analyzer output schemas for wallet and contract scans."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator

from app.blockchain.honeypot_simulation_state import HoneypotSimulationState
from app.core.analyzer_constants import ANALYZER_VERSION
from app.models.enums import (
    AdminType,
    CapabilityConfidence,
    CapabilityDetectionMethod,
    CapabilitySeverity,
    CentralizationLevel,
    ConfidenceLevel,
    ContractType,
    FundingSourceType,
    GovernanceType,
    HoneypotConfidence,
    HoneypotDetectionMethod,
    HoneypotFindingType,
    HoneypotSeverity,
    HoneypotSimulationStatus,
    ProxyType,
    RiskLevel,
    ScanDetectionMethod,
    ThreatLevel,
    UpgradeAuthority,
    WalletRelationshipType,
    WalletRole,
)


class GovernanceRoleData(BaseModel):
    """AccessControl role node with admin-role hierarchy link."""

    name: str
    role_id: str
    admin_role_name: str | None = None
    admin_role_id: str | None = None
    is_default_admin: bool = False


class GovernanceIntelligenceData(BaseModel):
    """Governance intelligence payload returned by GET /api/v1/scans/{id}."""

    governance_type: GovernanceType = GovernanceType.NONE
    upgrade_authority: UpgradeAuthority = UpgradeAuthority.NONE
    has_timelock: bool = False
    role_count: int = 0
    roles: list[GovernanceRoleData] = Field(default_factory=list)
    ownership_address: str | None = None
    ownership_renounced: bool = False
    source_confidence: ConfidenceLevel = ConfidenceLevel.LOW


class GovernanceAnalysisData(BaseModel):
    """Internal transfer object returned by GovernanceAnalyzer."""

    governance_type: GovernanceType = GovernanceType.NONE
    upgrade_authority: UpgradeAuthority = UpgradeAuthority.NONE
    has_timelock: bool = False
    role_count: int = 0
    roles: list[GovernanceRoleData] = Field(default_factory=list)
    ownership_address: str | None = None
    ownership_renounced: bool = False
    source_confidence: ConfidenceLevel = ConfidenceLevel.LOW


class CapabilityDetailData(BaseModel):
    """M3 per-capability intelligence node."""

    enabled: bool = False
    controller: str | None = None
    severity: CapabilitySeverity = CapabilitySeverity.LOW
    confidence: CapabilityConfidence = CapabilityConfidence.LOW
    detection_method: CapabilityDetectionMethod = CapabilityDetectionMethod.NONE


class HoneypotFindingData(BaseModel):
    """M4 per-finding honeypot intelligence node."""

    finding_type: HoneypotFindingType
    enabled: bool
    severity: HoneypotSeverity
    confidence: HoneypotConfidence
    detection_method: HoneypotDetectionMethod
    title: str
    description: str
    evidence: list[str] = Field(default_factory=list)


class HoneypotSummaryData(BaseModel):
    """Aggregate honeypot intelligence summary (M4)."""

    finding_count: int = 0
    critical_count: int = 0
    honeypot_score: int = 0
    honeypot_risk: HoneypotSeverity = HoneypotSeverity.LOW
    is_suspected: bool = False
    is_confirmed: bool = False


class HoneypotIntelligenceData(BaseModel):
    """Nested honeypot intelligence payload returned by GET /api/v1/scans/{id}."""

    summary: HoneypotSummaryData
    findings: list[HoneypotFindingData] = Field(default_factory=list)
    simulation: HoneypotSimulationState = Field(default_factory=HoneypotSimulationState)


class LiquidityPoolData(BaseModel):
    """Single DEX pool snapshot (M5.1)."""

    dex: str
    pair_address: str
    token0: str
    token1: str
    reserve0: str
    reserve1: str
    liquidity_native: float = 0.0
    liquidity_usd: Decimal = Decimal("0.00")
    lp_total_supply: str = "0"
    lp_owner: str | None = None
    lp_owner_balance: str = "0"
    liquidity_locked: bool = False
    liquidity_lock_percentage: Decimal = Decimal("0.00")
    lock_expiry: datetime | None = None


class LiquidityIntelligenceData(BaseModel):
    """Nested liquidity intelligence payload returned by GET /api/v1/scans/{id}."""

    has_liquidity: bool = False
    liquidity_usd: Decimal = Decimal("0.00")
    primary_dex: str | None = None
    pair_address: str | None = None
    lp_owner: str | None = None
    liquidity_locked: bool = False
    liquidity_lock_percentage: Decimal = Decimal("0.00")
    lock_expiry: datetime | None = None
    top_pools: list[LiquidityPoolData] = Field(default_factory=list)


class LiquidityAnalysisData(BaseModel):
    """Internal transfer object returned by LiquidityAnalyzer."""

    has_liquidity: bool = False
    liquidity_usd: Decimal = Decimal("0.00")
    primary_dex: str | None = None
    pair_address: str | None = None
    lp_owner: str | None = None
    liquidity_locked: bool = False
    liquidity_lock_percentage: Decimal = Decimal("0.00")
    lock_expiry: datetime | None = None
    top_pools: list[LiquidityPoolData] = Field(default_factory=list)


class WalletRoleNode(BaseModel):
    """Wallet role assignment relative to a scanned contract (M5.2)."""

    address: str
    role: WalletRole


class WalletOwnershipData(BaseModel):
    """Ownership and authority wallet mapping (M5.2)."""

    creator: str | None = None
    deployer: str | None = None
    owner: str | None = None
    proxy_admin: str | None = None
    treasury: str | None = None
    multisig: str | None = None
    timelock: str | None = None
    upgrade_authority: UpgradeAuthority | None = None
    roles: list[WalletRoleNode] = Field(default_factory=list)


class WalletFundingData(BaseModel):
    """Deployer funding history snapshot (M5.2)."""

    first_funding_tx_hash: str | None = None
    funding_wallet: str | None = None
    funding_source: FundingSourceType = FundingSourceType.UNKNOWN
    is_fresh_wallet: bool = False
    deployer_tx_count: int = 0
    contract_creation_tx_hash: str | None = None
    contract_creation_block: int | None = None


class WalletReputationData(BaseModel):
    """Wallet reputation flags (M5.2)."""

    known_scam: bool = False
    phishing: bool = False
    sanctioned: bool = False
    exploit_related: bool = False
    confidence: ConfidenceLevel = ConfidenceLevel.LOW


class WalletGraphNode(BaseModel):
    """Graph node for wallet relationship visualization (M5.2)."""

    id: str
    label: str
    role: WalletRole | None = None


class WalletGraphEdge(BaseModel):
    """Graph edge for wallet relationship visualization (M5.2)."""

    source: str
    target: str
    relationship: WalletRelationshipType


class WalletGraphData(BaseModel):
    """Graph-ready wallet relationship structure (M5.2)."""

    nodes: list[WalletGraphNode] = Field(default_factory=list)
    edges: list[WalletGraphEdge] = Field(default_factory=list)


class WalletIntelligenceData(BaseModel):
    """Nested wallet intelligence payload returned by GET /api/v1/scans/{id} (M5.2)."""

    ownership: WalletOwnershipData = Field(default_factory=WalletOwnershipData)
    funding: WalletFundingData = Field(default_factory=WalletFundingData)
    reputation: WalletReputationData = Field(default_factory=WalletReputationData)
    graph: WalletGraphData = Field(default_factory=WalletGraphData)
    wallet_risk_score: int = 0
    deployer_is_fresh: bool = False
    creator_owns_majority: bool = False
    lp_owner_is_creator: bool = False
    exchange_funded_deployer: bool = False
    tornado_funded_deployer: bool = False
    treasury_is_multisig: bool = False


class ProtocolConfidenceData(BaseModel):
    """Evidence-weighted protocol confidence (M6.1)."""

    score: int = 0
    level: ConfidenceLevel = ConfidenceLevel.LOW


class DexIntegrationData(BaseModel):
    """Structured DEX integration detected on the target contract."""

    name: str
    role: str
    confidence: int


class LendingIntegrationData(BaseModel):
    """Structured lending integration detected on the target contract."""

    name: str
    role: str
    confidence: int


class OracleIntegrationData(BaseModel):
    """Structured oracle integration detected on the target contract."""

    name: str
    confidence: int


class BridgeIntegrationData(BaseModel):
    """Structured bridge integration detected on the target contract."""

    name: str
    role: str
    confidence: int


class VaultIntegrationData(BaseModel):
    """Structured vault integration detected on the target contract."""

    name: str
    type: str
    confidence: int


class NftIntegrationData(BaseModel):
    """Structured NFT integration detected on the target contract."""

    standard: str
    marketplace: str = ""
    confidence: int


class GovernanceIntegrationData(BaseModel):
    """Structured governance integration detected on the target contract."""

    name: str
    confidence: int


class ProtocolRelationshipData(BaseModel):
    """Cross-protocol relationship edge (M6.3)."""

    source: str
    target: str
    relationship_type: str
    confidence: int
    detection_source: str


class ArchitectureGraphNodeData(BaseModel):
    """Architecture graph node (M6.3)."""

    id: str
    label: str
    node_type: str
    address: str | None = None


class ArchitectureGraphEdgeData(BaseModel):
    """Architecture graph edge (M6.3)."""

    source: str
    target: str
    relationship: str
    confidence: int
    detection_source: str


class ArchitectureGraphData(BaseModel):
    """Visualization-ready architecture graph (M6.3)."""

    nodes: list[ArchitectureGraphNodeData] = Field(default_factory=list)
    edges: list[ArchitectureGraphEdgeData] = Field(default_factory=list)


class ArchitectureSummaryData(BaseModel):
    """Data-driven architecture summary (M6.3)."""

    application_type: str = "unknown"
    protocol_stack: list[str] = Field(default_factory=list)
    oracle: str | None = None
    liquidity: str | None = None
    bridge: str | None = None
    governance: str | None = None
    upgradeability: str | None = None
    ownership: str | None = None


class ExternalDependencyData(BaseModel):
    """External protocol dependency (M6.4)."""

    category: str
    name: str
    role: str = ""
    confidence: int
    detection_source: str
    address: str | None = None


class TrustBoundaryData(BaseModel):
    """Trust boundary node (M6.4)."""

    boundary_type: str
    label: str
    confidence: int
    detection_source: str
    address: str | None = None


class PrivilegedEntityData(BaseModel):
    """Privileged control entity (M6.4)."""

    entity_type: str
    label: str
    confidence: int
    detection_source: str
    address: str | None = None


class AttackPathData(BaseModel):
    """Inferred attack path chain (M6.4)."""

    name: str
    steps: list[str] = Field(default_factory=list)
    confidence: int
    detection_source: str


class CriticalAssetData(BaseModel):
    """Critical asset exposed via dependencies (M6.4)."""

    asset_type: str
    label: str
    confidence: int
    address: str | None = None


class DependencyGraphNodeData(BaseModel):
    """Dependency graph node (M6.4)."""

    id: str
    label: str
    node_type: str
    address: str | None = None


class DependencyGraphEdgeData(BaseModel):
    """Dependency graph edge (M6.4)."""

    source: str
    target: str
    relationship: str
    confidence: int


class DependencyGraphData(BaseModel):
    """Threat dependency graph for visualization (M6.4)."""

    nodes: list[DependencyGraphNodeData] = Field(default_factory=list)
    edges: list[DependencyGraphEdgeData] = Field(default_factory=list)


class ThreatSurfaceData(BaseModel):
    """Threat and attack surface intelligence (M6.4)."""

    external_dependencies: list[ExternalDependencyData] = Field(default_factory=list)
    trust_boundaries: list[TrustBoundaryData] = Field(default_factory=list)
    privileged_entities: list[PrivilegedEntityData] = Field(default_factory=list)
    attack_paths: list[AttackPathData] = Field(default_factory=list)
    dependency_graph: DependencyGraphData = Field(default_factory=DependencyGraphData)
    critical_assets: list[CriticalAssetData] = Field(default_factory=list)


class ProtocolIntelligenceData(BaseModel):
    """Nested protocol intelligence payload returned by GET /api/v1/scans/{id} (M6.0+)."""

    protocol_family: str = "unknown"
    protocol_name: str = "unknown"
    protocol_type: str = "unknown"
    family: str = "unknown"
    name: str = "unknown"
    standards: list[str] = Field(default_factory=list)
    frameworks: list[str] = Field(default_factory=list)
    integrations: list[str] = Field(default_factory=list)
    proxy_type: str = "none"
    dexes: list[DexIntegrationData] = Field(default_factory=list)
    lending: list[LendingIntegrationData] = Field(default_factory=list)
    oracles: list[OracleIntegrationData] = Field(default_factory=list)
    bridges: list[BridgeIntegrationData] = Field(default_factory=list)
    vaults: list[VaultIntegrationData] = Field(default_factory=list)
    nfts: list[NftIntegrationData] = Field(default_factory=list)
    governance: list[GovernanceIntegrationData] = Field(default_factory=list)
    relationships: list[ProtocolRelationshipData] = Field(default_factory=list)
    architecture_graph: ArchitectureGraphData = Field(default_factory=ArchitectureGraphData)
    architecture_summary: ArchitectureSummaryData = Field(default_factory=ArchitectureSummaryData)
    threat_surface: ThreatSurfaceData = Field(default_factory=ThreatSurfaceData)
    confidence: ProtocolConfidenceData = Field(default_factory=ProtocolConfidenceData)
    detection_reasons: list[str] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def normalize_legacy_payload(cls, data):
        if not isinstance(data, dict):
            return data
        normalized = dict(data)
        if "family" not in normalized and "protocol_family" in normalized:
            normalized["family"] = normalized["protocol_family"]
        if "name" not in normalized and "protocol_name" in normalized:
            normalized["name"] = normalized["protocol_name"]
        confidence = normalized.get("confidence")
        if isinstance(confidence, str):
            normalized["confidence"] = {
                "score": _legacy_confidence_score(confidence),
                "level": confidence,
            }
        normalized.setdefault("relationships", [])
        normalized.setdefault("architecture_graph", {"nodes": [], "edges": []})
        normalized.setdefault("architecture_summary", {})
        normalized.setdefault("threat_surface", {})
        return normalized


def _legacy_confidence_score(level: str) -> int:
    mapping = {"high": 80, "medium": 55, "low": 20}
    return mapping.get(level, 0)


class ScanResultResponse(BaseModel):
    """On-chain analysis captured during a scan job (wallet or contract)."""

    chain_id: int = Field(..., examples=[11155111], description="EIP-155 chain ID from the RPC node.")
    latest_block: int = Field(..., examples=[12345678], description="Latest block height at scan time.")
    wallet_balance_wei: int | None = Field(
        None,
        examples=[1000000000000000000],
        description="Native chain currency balance in wei (wallet scans only).",
    )
    is_contract: bool | None = Field(
        None,
        examples=[True],
        description="True when runtime bytecode is non-empty (contract scans).",
    )
    bytecode_size: int | None = Field(
        None,
        examples=[24576],
        description="Runtime bytecode length in bytes (contract scans only).",
    )
    is_upgradeable: bool | None = Field(
        None,
        examples=[True],
        description="True when an EIP-1967 implementation address is stored (contract scans).",
    )
    implementation_address: str | None = Field(
        None,
        examples=["0xa231aa3388416ebc1b8f8a51b412327832524ca4"],
        description="EIP-1967 implementation contract address when upgradeable.",
    )
    admin_address: str | None = Field(
        None,
        examples=["0x1234567890123456789012345678901234567890"],
        description="EIP-1967 upgrade admin address (transparent proxy pattern).",
    )
    admin_type: AdminType | None = Field(
        None,
        examples=[AdminType.EOA, AdminType.MULTISIG],
        description="Classification of the upgrade admin wallet (eoa, contract, multisig).",
    )
    owner_address: str | None = Field(
        None,
        examples=["0xabcdefabcdefabcdefabcdefabcdefabcdefabcd"],
        description="Controlling address from ProxyAdmin owner() when admin is a contract.",
    )
    owner_type: AdminType | None = Field(
        None,
        examples=[AdminType.EOA],
        description="Classification of the traced ProxyAdmin owner address.",
    )
    is_timelock: bool | None = Field(
        None,
        examples=[True],
        description="True when upgrade authority uses an OpenZeppelin TimelockController.",
    )
    min_delay: int | None = Field(
        None,
        examples=[86400],
        description="Minimum delay in seconds from TimelockController.getMinDelay().",
    )
    mint_capability: bool | None = Field(
        None,
        examples=[True],
        description="True when the logic contract exposes mint/inflation capability.",
    )
    pause_capability: bool | None = Field(
        None,
        examples=[True],
        description="True when the logic contract exposes pause/unpause capability.",
    )
    blacklist_capability: bool | None = Field(
        None,
        examples=[False],
        description="True when the logic contract exposes blacklist/blocklist capability.",
    )
    ownership_capability: bool | None = Field(
        None,
        examples=[True],
        description="True when the logic contract exposes Ownable-style ownership controls.",
    )
    trading_enabled_control: bool | None = Field(
        None,
        examples=[True],
        description="True when admin can enable/disable trading (launch gate pattern).",
    )
    whitelist_control: bool | None = Field(
        None,
        examples=[False],
        description="True when contract exposes whitelist-based trading restrictions.",
    )
    blacklist_sell_blocking: bool | None = Field(
        None,
        examples=[True],
        description="True when blacklist/bot probes combine with sell-limit patterns.",
    )
    transfer_tax_control: bool | None = Field(
        None,
        examples=[True],
        description="True when contract exposes configurable buy/sell tax or fee controls.",
    )
    trade_simulated: bool | None = Field(
        None,
        examples=[True],
        description="True when Anvil fork trade simulation completed successfully.",
    )
    can_buy: bool | None = Field(
        None,
        examples=[True],
        description="Trade simulation buy path result (None when not simulated).",
    )
    can_sell: bool | None = Field(
        None,
        examples=[False],
        description="Trade simulation sell path result (None when not simulated).",
    )
    buy_tax_bps: int | None = Field(
        None,
        examples=[300],
        description="Measured buy tax in basis points from trade simulation.",
    )
    sell_tax_bps: int | None = Field(
        None,
        examples=[9900],
        description="Measured sell tax in basis points from trade simulation.",
    )
    risk_score: Decimal | None = Field(
        None,
        examples=[Decimal("100.00")],
        description="Rule-based rug-pull risk score 0–100 (contract scans).",
    )
    risk_level: RiskLevel | None = Field(
        None,
        examples=[RiskLevel.HIGH],
        description="Qualitative risk band derived from risk_score.",
    )
    risk_reasons: list[str] | None = Field(
        None,
        examples=[
            [
                "Contract uses an upgradeable EIP-1967 proxy pattern",
                "Upgrade admin address is exposed via EIP-1967 admin slot",
            ]
        ],
        description="Human-readable findings that contributed to the score.",
    )
    detection_method: ScanDetectionMethod | None = Field(
        None,
        examples=[ScanDetectionMethod.BYTECODE, ScanDetectionMethod.HYBRID],
        description="Intelligence technique: bytecode, source, simulation, or hybrid.",
    )
    analyzer_version: str | None = Field(
        None,
        examples=[ANALYZER_VERSION],
        description="ChainSentinel analyzer version that produced this result.",
    )
    contract_type: ContractType | None = Field(
        None,
        examples=[ContractType.ERC20, ContractType.TIMELOCK],
        description="High-level contract classification (contract scans).",
    )
    proxy_type: ProxyType | None = Field(
        None,
        examples=[ProxyType.EIP1967_TRANSPARENT, ProxyType.NONE],
        description="EIP-1967 proxy pattern when upgradeable (contract scans).",
    )
    is_verified: bool | None = Field(
        None,
        examples=[True, False],
        description="True when verified source is available on a block explorer.",
    )
    threat_level: ThreatLevel | None = Field(
        None,
        examples=[ThreatLevel.HIGH, ThreatLevel.CRITICAL],
        description="Exploit and rug-pull mechanics severity (Risk Engine V2).",
    )
    centralization_level: CentralizationLevel | None = Field(
        None,
        examples=[CentralizationLevel.HIGH, CentralizationLevel.LOW],
        description="Governance authority concentration (Risk Engine V2).",
    )
    confidence_level: ConfidenceLevel | None = Field(
        None,
        examples=[ConfidenceLevel.HIGH, ConfidenceLevel.MEDIUM],
        description="Assessment reliability based on evidence quality (Risk Engine V2).",
    )
    governance_type: GovernanceType | None = Field(
        None,
        examples=[GovernanceType.ACCESS_CONTROL, GovernanceType.TIMELOCK],
        description="Primary on-chain governance pattern (M2).",
    )
    upgrade_authority: UpgradeAuthority | None = Field(
        None,
        examples=[UpgradeAuthority.TIMELOCK, UpgradeAuthority.EOA],
        description="Effective upgrade authority classification (M2).",
    )
    role_count: int | None = Field(
        None,
        examples=[3],
        description="Number of AccessControl roles detected (M2).",
    )
    governance_roles: list[GovernanceRoleData] | None = Field(
        None,
        description="AccessControl role hierarchy nodes (M2).",
    )
    governance_ownership_address: str | None = Field(
        None,
        examples=["0x742d35cc6634c0532925a3b844bc9e7595f0beb0"],
        description="Ownable owner() on logic contract when detected (M2).",
    )
    governance_ownership_renounced: bool | None = Field(
        None,
        examples=[False],
        description="True when verified source or owner() indicates renounced ownership (M4.2).",
    )
    governance_source_confidence: ConfidenceLevel | None = Field(
        None,
        examples=[ConfidenceLevel.HIGH],
        description="Confidence in governance detections from verified source (M4.2).",
    )
    capability_count: int | None = Field(
        None,
        examples=[5],
        description="Number of enabled dangerous capabilities (M3).",
    )
    capabilities_detail: dict[str, CapabilityDetailData] | None = Field(
        None,
        description="Full M3 capability intelligence map keyed by capability id.",
    )
    honeypot_score: int | None = Field(
        None,
        examples=[62],
        description="Internal honeypot sub-score 0–100 (M4).",
    )
    honeypot_risk: HoneypotSeverity | None = Field(
        None,
        examples=[HoneypotSeverity.HIGH],
        description="Aggregate honeypot risk band (M4).",
    )
    honeypot_finding_count: int | None = Field(
        None,
        examples=[4],
        description="Number of enabled honeypot findings (M4).",
    )
    honeypot_is_suspected: bool | None = Field(
        None,
        examples=[True],
        description="True when high-severity heuristic honeypot signals are present (M4).",
    )
    honeypot_is_confirmed: bool | None = Field(
        None,
        examples=[False],
        description="True when simulation confirms users cannot exit (M4).",
    )
    honeypot_simulation_status: HoneypotSimulationStatus | None = Field(
        None,
        examples=[HoneypotSimulationStatus.NOT_RUN],
        description="Trade-path simulation lifecycle status (M4).",
    )
    honeypot_findings: list[HoneypotFindingData] | None = Field(
        None,
        description="Full M4 honeypot finding inventory.",
    )
    honeypot_simulation: HoneypotSimulationState | None = Field(
        None,
        description="Trade-path simulation snapshot (M4).",
    )
    liquidity_has_liquidity: bool | None = Field(
        None,
        description="True when at least one DEX pool with reserves was discovered (M5.1).",
    )
    liquidity_usd: Decimal | None = Field(
        None,
        description="Approximate primary pool liquidity depth in USD (M5.1).",
    )
    liquidity_primary_dex: str | None = Field(
        None,
        description="DEX identifier for the deepest discovered pool (M5.1).",
    )
    liquidity_pair_address: str | None = Field(
        None,
        description="Primary trading pair contract address (M5.1).",
    )
    liquidity_lp_owner: str | None = Field(
        None,
        description="Dominant LP token holder when detectable (M5.1).",
    )
    liquidity_locked: bool | None = Field(
        None,
        description="True when burned/locked LP exceeds threshold (M5.1).",
    )
    liquidity_lock_percentage: Decimal | None = Field(
        None,
        description="Percentage of LP supply held by burn/lock addresses (M5.1).",
    )
    liquidity_lock_expiry: datetime | None = Field(
        None,
        description="LP lock expiry when available from on-chain metadata (M5.1).",
    )
    liquidity_top_pools: list[LiquidityPoolData] | None = Field(
        None,
        description="Ranked pool snapshots across supported DEX providers (M5.1).",
    )
    wallet_creator: str | None = Field(
        None,
        description="Contract creator/deployer wallet when discoverable (M5.2).",
    )
    wallet_deployer: str | None = Field(
        None,
        description="Contract deployer from creation transaction (M5.2).",
    )
    wallet_owner: str | None = Field(
        None,
        description="Effective owner wallet from governance tracing (M5.2).",
    )
    wallet_treasury: str | None = Field(
        None,
        description="Treasury wallet when identified (M5.2).",
    )
    wallet_funding_source: FundingSourceType | None = Field(
        None,
        description="Classification of deployer first funding source (M5.2).",
    )
    wallet_funding_wallet: str | None = Field(
        None,
        description="Wallet that first funded the deployer (M5.2).",
    )
    wallet_is_fresh_deployer: bool | None = Field(
        None,
        description="True when deployer wallet appears newly created (M5.2).",
    )
    wallet_reputation_known_scam: bool | None = Field(
        None,
        description="True when deployer matches known scam denylist (M5.2).",
    )
    wallet_reputation_phishing: bool | None = Field(
        None,
        description="True when deployer matches phishing denylist (M5.2).",
    )
    wallet_reputation_sanctioned: bool | None = Field(
        None,
        description="True when deployer matches sanctioned denylist (M5.2).",
    )
    wallet_reputation_exploit_related: bool | None = Field(
        None,
        description="True when deployer matches exploit-related denylist (M5.2).",
    )
    wallet_reputation_confidence: ConfidenceLevel | None = Field(
        None,
        description="Confidence in wallet reputation signals (M5.2).",
    )
    wallet_lp_owner_is_creator: bool | None = Field(
        None,
        description="True when LP owner equals contract creator (M5.2).",
    )
    wallet_creator_owns_majority: bool | None = Field(
        None,
        description="True when creator controls owner or LP (M5.2).",
    )
    wallet_exchange_funded_deployer: bool | None = Field(
        None,
        description="True when deployer was funded from a known exchange (M5.2).",
    )
    wallet_tornado_funded_deployer: bool | None = Field(
        None,
        description="True when deployer was funded via Tornado Cash (M5.2).",
    )
    wallet_treasury_is_multisig: bool | None = Field(
        None,
        description="True when treasury authority is a multisig (M5.2).",
    )
    wallet_risk_score: int | None = Field(
        None,
        description="Internal wallet intelligence sub-score 0–100 (M5.2).",
    )
    wallet_relationship_graph: WalletGraphData | None = Field(
        None,
        description="Graph-ready wallet relationship structure (M5.2).",
    )
    protocol_intelligence: ProtocolIntelligenceData | None = Field(
        None,
        description="Protocol family, standards, frameworks, and proxy classification (M6.0).",
    )
    created_at: datetime = Field(..., description="UTC timestamp when analyzer output was persisted.")

    model_config = ConfigDict(from_attributes=True)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def capabilities(self) -> dict[str, CapabilityDetailData]:
        """Nested M3 capability intelligence for API consumers."""
        if self.capabilities_detail:
            return self.capabilities_detail
        return {}

    @computed_field  # type: ignore[prop-decorator]
    @property
    def governance(self) -> GovernanceIntelligenceData:
        """Nested governance intelligence for API consumers (M2)."""
        return GovernanceIntelligenceData(
            governance_type=self.governance_type or GovernanceType.NONE,
            upgrade_authority=self.upgrade_authority or UpgradeAuthority.NONE,
            has_timelock=bool(self.is_timelock),
            role_count=self.role_count or 0,
            roles=self.governance_roles or [],
            ownership_address=self.governance_ownership_address,
            ownership_renounced=bool(self.governance_ownership_renounced),
            source_confidence=self.governance_source_confidence or ConfidenceLevel.LOW,
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def honeypot(self) -> HoneypotIntelligenceData:
        """Nested honeypot intelligence for API consumers (M4)."""
        from app.blockchain.honeypot_intelligence import build_honeypot_intelligence_from_legacy

        if self.honeypot_findings is not None:
            summary = HoneypotSummaryData(
                finding_count=self.honeypot_finding_count or 0,
                critical_count=sum(
                    1
                    for finding in self.honeypot_findings
                    if finding.enabled and finding.severity == HoneypotSeverity.CRITICAL
                ),
                honeypot_score=self.honeypot_score or 0,
                honeypot_risk=self.honeypot_risk or HoneypotSeverity.LOW,
                is_suspected=bool(self.honeypot_is_suspected),
                is_confirmed=bool(self.honeypot_is_confirmed),
            )
            return HoneypotIntelligenceData(
                summary=summary,
                findings=self.honeypot_findings,
                simulation=self.honeypot_simulation or HoneypotSimulationState(),
            )

        findings, summary, simulation = build_honeypot_intelligence_from_legacy(
            trading_enabled_control=self.trading_enabled_control,
            whitelist_control=self.whitelist_control,
            blacklist_sell_blocking=self.blacklist_sell_blocking,
            transfer_tax_control=self.transfer_tax_control,
            trade_simulated=self.trade_simulated,
            can_buy=self.can_buy,
            can_sell=self.can_sell,
            buy_tax_bps=self.buy_tax_bps,
            sell_tax_bps=self.sell_tax_bps,
        )
        return HoneypotIntelligenceData(
            summary=summary,
            findings=findings,
            simulation=simulation,
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def liquidity(self) -> LiquidityIntelligenceData:
        """Nested liquidity intelligence for API consumers (M5.1)."""
        if self.liquidity_top_pools is not None:
            return LiquidityIntelligenceData(
                has_liquidity=bool(self.liquidity_has_liquidity),
                liquidity_usd=self.liquidity_usd or Decimal("0.00"),
                primary_dex=self.liquidity_primary_dex,
                pair_address=self.liquidity_pair_address,
                lp_owner=self.liquidity_lp_owner,
                liquidity_locked=bool(self.liquidity_locked),
                liquidity_lock_percentage=self.liquidity_lock_percentage or Decimal("0.00"),
                lock_expiry=self.liquidity_lock_expiry,
                top_pools=self.liquidity_top_pools,
            )
        return LiquidityIntelligenceData()

    @computed_field  # type: ignore[prop-decorator]
    @property
    def wallet_intelligence(self) -> WalletIntelligenceData:
        """Nested wallet intelligence for API consumers (M5.2)."""
        if self.wallet_risk_score is not None:
            return WalletIntelligenceData(
                ownership=WalletOwnershipData(
                    creator=self.wallet_creator,
                    deployer=self.wallet_deployer,
                    owner=self.wallet_owner,
                    treasury=self.wallet_treasury,
                ),
                funding=WalletFundingData(
                    funding_wallet=self.wallet_funding_wallet,
                    funding_source=self.wallet_funding_source or FundingSourceType.UNKNOWN,
                    is_fresh_wallet=bool(self.wallet_is_fresh_deployer),
                ),
                reputation=WalletReputationData(
                    known_scam=bool(self.wallet_reputation_known_scam),
                    phishing=bool(self.wallet_reputation_phishing),
                    sanctioned=bool(self.wallet_reputation_sanctioned),
                    exploit_related=bool(self.wallet_reputation_exploit_related),
                    confidence=self.wallet_reputation_confidence or ConfidenceLevel.LOW,
                ),
                graph=self.wallet_relationship_graph or WalletGraphData(),
                wallet_risk_score=self.wallet_risk_score or 0,
                deployer_is_fresh=bool(self.wallet_is_fresh_deployer),
                creator_owns_majority=bool(self.wallet_creator_owns_majority),
                lp_owner_is_creator=bool(self.wallet_lp_owner_is_creator),
                exchange_funded_deployer=bool(self.wallet_exchange_funded_deployer),
                tornado_funded_deployer=bool(self.wallet_tornado_funded_deployer),
                treasury_is_multisig=bool(self.wallet_treasury_is_multisig),
            )
        return WalletIntelligenceData()

    @computed_field  # type: ignore[prop-decorator]
    @property
    def wallet_balance_eth(self) -> str | None:
        """Human-readable ETH balance derived from wei (wallet scans only)."""
        if self.wallet_balance_wei is None:
            return None
        eth = Decimal(self.wallet_balance_wei) / Decimal(10**18)
        return format(eth, "f")


class WalletAnalysisData(BaseModel):
    """Internal transfer object returned by WalletAnalyzer."""

    chain_id: int
    latest_block: int
    wallet_balance_wei: int


class ProxyAnalysisData(BaseModel):
    """Internal transfer object returned by ProxyAnalyzer."""

    is_upgradeable: bool
    implementation_address: str | None


class AdminAnalysisData(BaseModel):
    """Internal transfer object returned by AdminAnalyzer."""

    admin_address: str | None


class ProxyAdminOwnerAnalysisData(BaseModel):
    """Internal transfer object returned by ProxyAdminAnalyzer."""

    owner_address: str | None
    owner_type: AdminType | None


class TimelockAnalysisData(BaseModel):
    """Internal transfer object returned by TimelockAnalyzer."""

    is_timelock: bool
    min_delay: int | None


class ContractClassificationData(BaseModel):
    """Internal transfer object returned by ContractClassifier."""

    contract_type: ContractType
    proxy_type: ProxyType
    is_verified: bool


class CapabilityAnalysisData(BaseModel):
    """Internal transfer object returned by CapabilityAnalyzer."""

    mint_capability: bool
    pause_capability: bool
    blacklist_capability: bool
    ownership_capability: bool
    detection_method: CapabilityDetectionMethod = CapabilityDetectionMethod.NONE
    capability_count: int = 0
    capabilities: dict[str, CapabilityDetailData] = Field(default_factory=dict)


class HoneypotAnalysisData(BaseModel):
    """Internal transfer object returned by HoneypotAnalyzer."""

    trading_enabled_control: bool
    whitelist_control: bool
    blacklist_sell_blocking: bool
    transfer_tax_control: bool
    can_buy: bool | None = None
    can_sell: bool | None = None
    buy_tax_bps: int | None = None
    sell_tax_bps: int | None = None
    trade_simulated: bool = False
    detection_method: HoneypotDetectionMethod = HoneypotDetectionMethod.NONE
    summary: HoneypotSummaryData = Field(default_factory=HoneypotSummaryData)
    findings: list[HoneypotFindingData] = Field(default_factory=list)
    simulation: HoneypotSimulationState = Field(default_factory=HoneypotSimulationState)


class ContractAnalysisData(BaseModel):
    """Internal transfer object returned by ContractAnalyzer."""

    chain_id: int
    latest_block: int
    is_contract: bool
    bytecode_size: int
    is_upgradeable: bool
    implementation_address: str | None
    admin_address: str | None
    admin_type: AdminType | None
    owner_address: str | None
    owner_type: AdminType | None
    is_timelock: bool
    min_delay: int | None
    mint_capability: bool
    pause_capability: bool
    blacklist_capability: bool
    ownership_capability: bool
    trading_enabled_control: bool
    whitelist_control: bool
    blacklist_sell_blocking: bool
    transfer_tax_control: bool
    can_buy: bool | None
    can_sell: bool | None
    buy_tax_bps: int | None
    sell_tax_bps: int | None
    trade_simulated: bool
    risk_score: Decimal
    risk_level: RiskLevel
    risk_reasons: list[str]
    detection_method: ScanDetectionMethod | None = None
    analyzer_version: str = ANALYZER_VERSION
    contract_type: ContractType | None = None
    proxy_type: ProxyType | None = None
    is_verified: bool | None = None
    threat_level: ThreatLevel | None = None
    centralization_level: CentralizationLevel | None = None
    confidence_level: ConfidenceLevel | None = None
    governance_type: GovernanceType | None = None
    upgrade_authority: UpgradeAuthority | None = None
    role_count: int | None = None
    governance_roles: list[GovernanceRoleData] | None = None
    governance_ownership_address: str | None = None
    governance_ownership_renounced: bool | None = None
    governance_source_confidence: ConfidenceLevel | None = None
    capability_count: int | None = None
    capabilities_detail: dict[str, CapabilityDetailData] | None = None
    honeypot_score: int | None = None
    honeypot_risk: HoneypotSeverity | None = None
    honeypot_finding_count: int | None = None
    honeypot_is_suspected: bool | None = None
    honeypot_is_confirmed: bool | None = None
    honeypot_simulation_status: HoneypotSimulationStatus | None = None
    honeypot_findings: list[HoneypotFindingData] | None = None
    honeypot_simulation: HoneypotSimulationState | None = None
    liquidity_has_liquidity: bool | None = None
    liquidity_usd: Decimal | None = None
    liquidity_primary_dex: str | None = None
    liquidity_pair_address: str | None = None
    liquidity_lp_owner: str | None = None
    liquidity_locked: bool | None = None
    liquidity_lock_percentage: Decimal | None = None
    liquidity_lock_expiry: datetime | None = None
    liquidity_top_pools: list[LiquidityPoolData] | None = None
    wallet_creator: str | None = None
    wallet_deployer: str | None = None
    wallet_owner: str | None = None
    wallet_treasury: str | None = None
    wallet_funding_source: FundingSourceType | None = None
    wallet_funding_wallet: str | None = None
    wallet_is_fresh_deployer: bool | None = None
    wallet_reputation_known_scam: bool | None = None
    wallet_reputation_phishing: bool | None = None
    wallet_reputation_sanctioned: bool | None = None
    wallet_reputation_exploit_related: bool | None = None
    wallet_reputation_confidence: ConfidenceLevel | None = None
    wallet_lp_owner_is_creator: bool | None = None
    wallet_creator_owns_majority: bool | None = None
    wallet_exchange_funded_deployer: bool | None = None
    wallet_tornado_funded_deployer: bool | None = None
    wallet_treasury_is_multisig: bool | None = None
    wallet_risk_score: int | None = None
    wallet_relationship_graph: WalletGraphData | None = None
    protocol_intelligence: ProtocolIntelligenceData | None = None
