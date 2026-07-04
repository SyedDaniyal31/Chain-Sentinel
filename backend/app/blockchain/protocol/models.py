"""Protocol intelligence domain models (M6.0)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class ProtocolStandard(StrEnum):
    """EIP / ERC standards detected on the logic contract."""

    ERC20 = "ERC20"
    ERC721 = "ERC721"
    ERC1155 = "ERC1155"
    ERC4626 = "ERC4626"


class ProtocolFramework(StrEnum):
    """Smart contract framework patterns (primarily OpenZeppelin)."""

    OPENZEPPELIN_OWNABLE = "OpenZeppelin Ownable"
    OPENZEPPELIN_ACCESS_CONTROL = "OpenZeppelin AccessControl"
    OPENZEPPELIN_PAUSABLE = "OpenZeppelin Pausable"
    OPENZEPPELIN_TIMELOCK_CONTROLLER = "OpenZeppelin TimelockController"


class ProtocolProxyKind(StrEnum):
    """Upgrade proxy pattern classification for M6.0 protocol intelligence."""

    NONE = "none"
    ERC1967 = "erc1967"
    UUPS = "uups"
    BEACON = "beacon"
    TRANSPARENT = "transparent"
    MINIMAL_PROXY = "minimal_proxy"


class ProtocolFamily(StrEnum):
    """High-level protocol family bucket."""

    TOKEN = "token"
    NFT = "nft"
    VAULT = "vault"
    GOVERNANCE = "governance"
    PROXY = "proxy"
    INFRASTRUCTURE = "infrastructure"
    DEX = "dex"
    LENDING = "lending"
    ORACLE = "oracle"
    STABLECOIN = "stablecoin"
    BRIDGE = "bridge"
    UNKNOWN = "unknown"


class ProtocolType(StrEnum):
    """Fine-grained protocol type label."""

    FUNGIBLE_TOKEN = "fungible_token"
    NON_FUNGIBLE_TOKEN = "non_fungible_token"
    MULTI_TOKEN = "multi_token"
    TOKEN_VAULT = "token_vault"
    TIMELOCK = "timelock"
    UPGRADEABLE_PROXY = "upgradeable_proxy"
    MINIMAL_PROXY = "minimal_proxy"
    GOVERNANCE = "governance"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class StandardDetection:
    """Result of a single standard detector."""

    standard: ProtocolStandard
    detected: bool
    reason: str
    confidence: str = "medium"


@dataclass(frozen=True, slots=True)
class FrameworkDetection:
    """Result of a single framework detector."""

    framework: ProtocolFramework
    detected: bool
    reason: str
    confidence: str = "medium"


@dataclass(frozen=True, slots=True)
class ProxyDetection:
    """Result of proxy pattern detection."""

    proxy_kind: ProtocolProxyKind
    detected: bool
    reason: str
    confidence: str = "medium"


@dataclass(frozen=True, slots=True)
class DexDetectionResult:
    """Structured DEX protocol detection (M6.1)."""

    name: str
    role: str
    confidence: int


@dataclass(frozen=True, slots=True)
class LendingDetectionResult:
    """Structured lending protocol detection (M6.1)."""

    name: str
    role: str
    confidence: int


@dataclass(frozen=True, slots=True)
class OracleDetectionResult:
    """Structured oracle protocol detection (M6.1)."""

    name: str
    confidence: int


@dataclass(frozen=True, slots=True)
class BridgeDetectionResult:
    """Structured bridge protocol detection (M6.2)."""

    name: str
    role: str
    confidence: int


@dataclass(frozen=True, slots=True)
class VaultDetectionResult:
    """Structured vault protocol detection (M6.2)."""

    name: str
    type: str
    confidence: int


@dataclass(frozen=True, slots=True)
class NftDetectionResult:
    """Structured NFT protocol detection (M6.2)."""

    standard: str
    marketplace: str
    confidence: int


@dataclass(frozen=True, slots=True)
class GovernanceDetectionResult:
    """Structured governance protocol detection (M6.2)."""

    name: str
    confidence: int


@dataclass(frozen=True, slots=True)
class ProtocolConfidenceScore:
    """Evidence-weighted confidence score (M6.1)."""

    score: int
    level: str


@dataclass
class ProtocolDetectionContext:
    """Inputs shared across M6.0+ protocol detectors."""

    target_address: str
    bytecode: bytes
    logic_bytecode: bytes
    chain_id: int = 1
    implementation_address: str | None = None
    admin_address: str | None = None
    is_timelock_hint: bool = False
    is_verified: bool = False
    verified_source_code: str | None = None
    contract_name: str | None = None


@dataclass
class ProtocolDetectionBundle:
    """Aggregated raw detector output before API shaping."""

    standards: list[StandardDetection] = field(default_factory=list)
    frameworks: list[FrameworkDetection] = field(default_factory=list)
    proxy: ProxyDetection | None = None
    integrations: list[str] = field(default_factory=list)
    dexes: list[DexDetectionResult] = field(default_factory=list)
    lending: list[LendingDetectionResult] = field(default_factory=list)
    oracles: list[OracleDetectionResult] = field(default_factory=list)
    bridges: list[BridgeDetectionResult] = field(default_factory=list)
    vaults: list[VaultDetectionResult] = field(default_factory=list)
    nfts: list[NftDetectionResult] = field(default_factory=list)
    governance: list[GovernanceDetectionResult] = field(default_factory=list)
    detection_reasons: list[str] = field(default_factory=list)
    verified_source_code: str | None = None
    contract_name: str | None = None
