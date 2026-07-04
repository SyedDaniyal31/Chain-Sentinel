"""Shared risk scoring weights and reason strings (M7.1)."""

from decimal import Decimal


# Point weights for proxy/implementation findings.
SCORE_UPGRADEABLE = 35
SCORE_IMPLEMENTATION = 30

# Admin slot scoring varies by effective upgrade authority type.
SCORE_ADMIN_EOA = 35
SCORE_ADMIN_CONTRACT = 28
SCORE_ADMIN_MULTISIG = 15
SCORE_ADMIN_TIMELOCK = 12

# Capability-based risk weights (independent of governance findings).
SCORE_MINT_CAPABILITY = 20
SCORE_PAUSE_CAPABILITY = 15
SCORE_BLACKLIST_CAPABILITY = 25
SCORE_OWNERSHIP_CAPABILITY = 10

# Honeypot / trading-restriction weights (Rug Pull Detector V2).
SCORE_TRADING_ENABLED_CONTROL = 18
SCORE_WHITELIST_CONTROL = 20
SCORE_BLACKLIST_SELL_BLOCKING = 28
SCORE_TRANSFER_TAX_CONTROL = 22

# Trade simulation weights (Rug Pull Detector V3 — confirmed on Anvil fork).
SCORE_SIM_BUY_BLOCKED = 15
SCORE_SIM_SELL_BLOCKED = 35
SCORE_SIM_HIGH_BUY_TAX = 12
SCORE_SIM_HIGH_SELL_TAX = 25
HIGH_TAX_BPS_THRESHOLD = 5000

REASON_UPGRADEABLE = "Contract uses an upgradeable EIP-1967 proxy pattern"
REASON_IMPLEMENTATION = "Implementation contract address is exposed via storage slot"
REASON_ADMIN_EOA = (
    "Upgrade admin is an externally owned account (elevated single-key upgrade risk)"
)
REASON_ADMIN_CONTRACT = "Upgrade admin is a smart contract (review ProxyAdmin or timelock)"
REASON_ADMIN_MULTISIG = "Upgrade admin appears to be a Gnosis Safe-style multisig"
REASON_PROXYADMIN_OWNER = "ProxyAdmin owner() traced to controlling address"
REASON_NOT_CONTRACT = "Target address has no contract bytecode"
REASON_NO_UPGRADE_SIGNALS = "No upgradeability indicators detected"
REASON_MINT_CAPABILITY = "Contract exposes mint capability (supply inflation risk)"
REASON_PAUSE_CAPABILITY = "Contract exposes pause capability (user funds may be frozen)"
REASON_BLACKLIST_CAPABILITY = (
    "Contract exposes blacklist capability (selective transfer blocking)"
)
REASON_OWNERSHIP_CAPABILITY = (
    "Contract exposes centralized ownership controls (transferOwnership)"
)
REASON_TRADING_ENABLED_CONTROL = (
    "Contract exposes trading launch controls (enableTrading / openTrading)"
)
REASON_WHITELIST_CONTROL = (
    "Contract exposes whitelist controls (selective trading gate)"
)
REASON_BLACKLIST_SELL_BLOCKING = (
    "Contract exposes blacklist and sell-restriction patterns (honeypot risk)"
)
REASON_TRANSFER_TAX_CONTROL = (
    "Contract exposes configurable transfer tax / fee controls"
)
REASON_SIM_BUY_BLOCKED = "Trade simulation confirmed buy path reverts on fork"
REASON_SIM_SELL_BLOCKED = "Trade simulation confirmed sell path reverts (honeypot)"
REASON_SIM_HIGH_BUY_TAX = "Trade simulation measured elevated buy tax ({tax_bps} bps)"
REASON_SIM_HIGH_SELL_TAX = "Trade simulation measured elevated sell tax ({tax_bps} bps)"

REASON_NO_LIQUIDITY = "No DEX liquidity pool discovered for this token"
REASON_LOW_LIQUIDITY = "Primary pool liquidity depth is very low (${usd})"
REASON_UNLOCKED_LP = "LP tokens appear unlocked (no significant burn/lock detected)"
REASON_SINGLE_WALLET_LP = "Primary LP ownership concentrated in a single wallet"

REASON_FRESH_DEPLOYER = "Contract deployer wallet appears newly created (fresh wallet)"
REASON_CREATOR_OWNS_MAJORITY = "Creator wallet controls owner or LP concentration"
REASON_LP_OWNER_IS_CREATOR = "LP owner wallet matches contract creator (rug-pull pattern)"
REASON_EXCHANGE_FUNDED_DEPLOYER = "Deployer funded from a known exchange (lower anonymity risk)"
REASON_TORNADO_FUNDED_DEPLOYER = "Deployer funded via Tornado Cash mixer (elevated anonymity risk)"
REASON_TREASURY_MULTISIG = "Treasury or admin authority appears to be a multisig"
REASON_WALLET_KNOWN_SCAM = "Deployer or owner wallet matches known scam/sanctioned denylist"

LOW_LIQUIDITY_USD = Decimal("1000.00")
SCORE_NO_LIQUIDITY = 30
SCORE_LOW_LIQUIDITY = 18
SCORE_UNLOCKED_LP = 22
SCORE_SINGLE_WALLET_LP = 15
SCORE_FRESH_DEPLOYER = 12
SCORE_CREATOR_OWNS_MAJORITY = 25
SCORE_LP_OWNER_IS_CREATOR = 18
SCORE_EXCHANGE_FUNDED_DEPLOYER = -5
SCORE_TORNADO_FUNDED_DEPLOYER = 35
SCORE_TREASURY_MULTISIG = -10
SCORE_WALLET_KNOWN_SCAM = 40
THREAT_NO_LIQUIDITY = 25
THREAT_LOW_LIQUIDITY = 12
THREAT_UNLOCKED_LP = 18

LOW_MAX = Decimal("33.00")
MEDIUM_MAX = Decimal("66.00")

# Threat dimension weights (exploit mechanics — excludes governance authority type).
THREAT_UPGRADEABLE = 18
THREAT_IMPLEMENTATION = 12
THREAT_MINT = 22
THREAT_PAUSE = 18
THREAT_BLACKLIST = 28
THREAT_OWNERSHIP = 8
THREAT_TRADING_ENABLED = 20
THREAT_WHITELIST = 22
THREAT_BLACKLIST_SELL = 30
THREAT_TRANSFER_TAX = 24
THREAT_SIM_SELL_BLOCKED = 40
THREAT_SIM_BUY_BLOCKED = 18
THREAT_SIM_HIGH_SELL_TAX = 28
THREAT_SIM_HIGH_BUY_TAX = 14

THREAT_LOW_MAX = 24
THREAT_MEDIUM_MAX = 49
THREAT_HIGH_MAX = 74

# Centralization dimension weights (governance concentration).
CENTRAL_ADMIN_EOA = 45
CENTRAL_ADMIN_CONTRACT = 32
CENTRAL_ADMIN_MULTISIG = 22
CENTRAL_ADMIN_TIMELOCK = 12
CENTRAL_OWNERSHIP_CAPABILITY = 22
CENTRAL_UPGRADEABLE_UNKNOWN_ADMIN = 28

CENTRAL_LOW_MAX = 20
CENTRAL_MEDIUM_MAX = 35

# Confidence dimension weights (assessment reliability).
CONFIDENCE_VERIFIED_SOURCE = 35
CONFIDENCE_CLASSIFICATION = 20
CONFIDENCE_PROXY_RESOLVED = 20
CONFIDENCE_TRADE_SIMULATED = 20
CONFIDENCE_BYTECODE_CONFIRMED = 10
CONFIDENCE_DETECTION_SOURCE = 15
CONFIDENCE_DETECTION_HYBRID = 12
CONFIDENCE_DETECTION_SIMULATION = 10
CONFIDENCE_DETECTION_BYTECODE = 10
CONFIDENCE_DETECTION_NONE = 5
CONFIDENCE_PROXY_UNRESOLVED_PENALTY = 15
CONFIDENCE_EOA_CONFIRMED = 45

CONFIDENCE_LOW_MAX = 39
CONFIDENCE_MEDIUM_MAX = 64


def timelock_reason(min_delay: int | None) -> str:
    """Build a risk reason string for timelock-governed upgrade authority."""
    if min_delay is not None:
        return (
            f"Upgrade authority protected by TimelockController (min delay {min_delay}s)"
        )
    return "Upgrade authority protected by TimelockController"
