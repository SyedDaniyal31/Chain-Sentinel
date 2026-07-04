"""M4 honeypot finding catalog: selectors, severities, and metadata."""

from dataclasses import dataclass

from app.blockchain.honeypot import (
    BLACKLIST_PROBE_FUNCTION_NAMES,
    BLACKLIST_PROBE_SELECTORS,
    SELL_RESTRICTION_FUNCTION_NAMES,
    SELL_RESTRICTION_SELECTORS,
    TRADING_ENABLED_FUNCTION_NAMES,
    TRADING_ENABLED_SELECTORS,
    TRANSFER_TAX_FUNCTION_NAMES,
    TRANSFER_TAX_SELECTORS,
    WHITELIST_FUNCTION_NAMES,
    WHITELIST_SELECTORS,
)
from app.models.enums import HoneypotFindingType, HoneypotSeverity

ANTI_BOT_SELECTORS: frozenset[bytes] = frozenset(
    bytes.fromhex(selector)
    for selector in ("9c0db5f3", "3bbac579")
)

ANTI_BOT_FUNCTION_NAMES: frozenset[str] = frozenset(
    name.lower() for name in ("setBots", "isBot", "antiBot")
)

MODIFIABLE_TAX_SELECTORS: frozenset[bytes] = frozenset(
    bytes.fromhex(selector)
    for selector in ("6db79437", "0b78f9c0", "ec1f3f63")
)

MODIFIABLE_TAX_FUNCTION_NAMES: frozenset[str] = frozenset(
    name.lower() for name in ("updateFees", "setFees", "reduceFee", "setCustomTax")
)


@dataclass(frozen=True, slots=True)
class HoneypotFindingDefinition:
    """Static metadata for a detectable honeypot finding."""

    finding_type: HoneypotFindingType
    title: str
    description: str
    category: str
    default_severity: HoneypotSeverity
    selectors: frozenset[bytes]
    function_names: frozenset[str]
    simulation_only: bool = False
    disabled_description: str | None = None


HONEYPOT_CATALOG: tuple[HoneypotFindingDefinition, ...] = (
    HoneypotFindingDefinition(
        finding_type=HoneypotFindingType.TRADING_GATE,
        title="Trading launch gate",
        description="Owner can enable trading after liquidity is added.",
        category="launch_control",
        default_severity=HoneypotSeverity.HIGH,
        selectors=TRADING_ENABLED_SELECTORS,
        function_names=TRADING_ENABLED_FUNCTION_NAMES,
    ),
    HoneypotFindingDefinition(
        finding_type=HoneypotFindingType.WHITELIST_RESTRICTION,
        title="Whitelist restriction",
        description="Only approved wallets may transfer tokens.",
        category="access_control",
        default_severity=HoneypotSeverity.MEDIUM,
        selectors=WHITELIST_SELECTORS,
        function_names=WHITELIST_FUNCTION_NAMES,
    ),
    HoneypotFindingDefinition(
        finding_type=HoneypotFindingType.BLACKLIST_PROBE,
        title="Blacklist probe",
        description="Contract exposes wallet blocking before transfer.",
        category="censorship",
        default_severity=HoneypotSeverity.CRITICAL,
        selectors=BLACKLIST_PROBE_SELECTORS,
        function_names=BLACKLIST_PROBE_FUNCTION_NAMES,
    ),
    HoneypotFindingDefinition(
        finding_type=HoneypotFindingType.SELL_RESTRICTION,
        title="Sell restriction",
        description="Contract exposes sell-limit or max-transaction controls.",
        category="exit_limit",
        default_severity=HoneypotSeverity.HIGH,
        selectors=SELL_RESTRICTION_SELECTORS,
        function_names=SELL_RESTRICTION_FUNCTION_NAMES,
    ),
    HoneypotFindingDefinition(
        finding_type=HoneypotFindingType.TRANSFER_TAX_CONTROL,
        title="Transfer tax control",
        description="Admin can configure buy or sell fees on transfers.",
        category="fee_admin",
        default_severity=HoneypotSeverity.HIGH,
        selectors=TRANSFER_TAX_SELECTORS,
        function_names=TRANSFER_TAX_FUNCTION_NAMES,
    ),
    HoneypotFindingDefinition(
        finding_type=HoneypotFindingType.MODIFIABLE_TAX,
        title="Modifiable tax",
        description="Contract exposes dynamic or updatable fee controls.",
        category="dynamic_rug",
        default_severity=HoneypotSeverity.HIGH,
        selectors=MODIFIABLE_TAX_SELECTORS,
        function_names=MODIFIABLE_TAX_FUNCTION_NAMES,
    ),
    HoneypotFindingDefinition(
        finding_type=HoneypotFindingType.ANTI_BOT_PATTERN,
        title="Anti-bot pattern",
        description="Bot-detection or anti-MEV gate may block organic traders.",
        category="mev_gate",
        default_severity=HoneypotSeverity.MEDIUM,
        selectors=ANTI_BOT_SELECTORS,
        function_names=ANTI_BOT_FUNCTION_NAMES,
    ),
    HoneypotFindingDefinition(
        finding_type=HoneypotFindingType.HIGH_BUY_TAX,
        title="Elevated buy tax",
        description="Measured buy tax exceeds threshold.",
        category="economic",
        default_severity=HoneypotSeverity.MEDIUM,
        selectors=frozenset(),
        function_names=frozenset(),
        simulation_only=True,
        disabled_description="Not tested — simulation not run.",
    ),
    HoneypotFindingDefinition(
        finding_type=HoneypotFindingType.HIGH_SELL_TAX,
        title="Elevated sell tax",
        description="Measured sell tax exceeds threshold.",
        category="economic",
        default_severity=HoneypotSeverity.HIGH,
        selectors=frozenset(),
        function_names=frozenset(),
        simulation_only=True,
        disabled_description="Not tested — simulation not run.",
    ),
    HoneypotFindingDefinition(
        finding_type=HoneypotFindingType.BUY_PATH_BLOCKED,
        title="Buy path blocked",
        description="Simulated buy path failed on fork.",
        category="liquidity_trap",
        default_severity=HoneypotSeverity.HIGH,
        selectors=frozenset(),
        function_names=frozenset(),
        simulation_only=True,
        disabled_description="Not tested — simulation not run.",
    ),
    HoneypotFindingDefinition(
        finding_type=HoneypotFindingType.SELL_PATH_BLOCKED,
        title="Sell path blocked",
        description="Simulated sell path failed on fork.",
        category="honeypot",
        default_severity=HoneypotSeverity.CRITICAL,
        selectors=frozenset(),
        function_names=frozenset(),
        simulation_only=True,
        disabled_description="Not tested — simulation not run.",
    ),
    HoneypotFindingDefinition(
        finding_type=HoneypotFindingType.TRANSFER_PATH_BLOCKED,
        title="Transfer path blocked",
        description="Simulated wallet-to-wallet transfer failed on fork.",
        category="wallet_trap",
        default_severity=HoneypotSeverity.HIGH,
        selectors=frozenset(),
        function_names=frozenset(),
        simulation_only=True,
        disabled_description="Not tested — simulation not run.",
    ),
    HoneypotFindingDefinition(
        finding_type=HoneypotFindingType.HONEYPOT_CONFIRMED,
        title="Honeypot confirmed",
        description="Simulation confirmed users cannot exit positions.",
        category="composite",
        default_severity=HoneypotSeverity.CRITICAL,
        selectors=frozenset(),
        function_names=frozenset(),
        simulation_only=True,
        disabled_description="Not tested — simulation not run.",
    ),
)

HONEYPOT_FINDING_KEYS: frozenset[str] = frozenset(
    definition.finding_type.value for definition in HONEYPOT_CATALOG
)
