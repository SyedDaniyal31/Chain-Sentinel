"""M3 capability catalog: selectors, roles, and default severity by category."""

from dataclasses import dataclass

from app.blockchain.honeypot import (
    BLACKLIST_PROBE_SELECTORS,
    TRADING_ENABLED_SELECTORS,
    TRANSFER_TAX_SELECTORS,
    WHITELIST_SELECTORS,
)
from app.models.enums import CapabilitySeverity

BURN_SELECTORS: frozenset[bytes] = frozenset(
    bytes.fromhex(selector)
    for selector in (
        "42966c68",  # burn(uint256)
        "79cc6790",  # burnFrom(address,uint256)
        "9dc29fac",  # burn(address)
    )
)

FREEZE_SELECTORS: frozenset[bytes] = frozenset(
    bytes.fromhex(selector)
    for selector in (
        "862b482f",  # freeze(address)
        "0752c27c",  # unfreeze(address)
    )
)

SEIZE_SELECTORS: frozenset[bytes] = frozenset({bytes.fromhex("83f12fec")})

COOLDOWN_SELECTORS: frozenset[bytes] = frozenset(
    bytes.fromhex(selector)
    for selector in (
        "bcd76e26",  # setCooldownEnabled(bool)
        "616c658b",  # setTransferDelay(uint256)
    )
)

GRANT_ROLE_SELECTOR = bytes.fromhex("2f2ff15d")
REVOKE_ROLE_SELECTOR = bytes.fromhex("d547741f")


@dataclass(frozen=True, slots=True)
class CapabilityDefinition:
    """Static metadata for a detectable contract capability."""

    key: str
    label: str
    category: str
    selectors: frozenset[bytes]
    function_names: frozenset[str]
    access_control_role: str | None
    default_severity: CapabilitySeverity


CAPABILITY_CATALOG: tuple[CapabilityDefinition, ...] = (
    CapabilityDefinition(
        key="mint",
        label="Mint",
        category="token_control",
        selectors=frozenset(
            bytes.fromhex(s)
            for s in ("40c10f19", "a0712d68", "6a627842", "449a52f8")
        ),
        function_names=frozenset({"mint", "mintto", "_mint"}),
        access_control_role="MINTER_ROLE",
        default_severity=CapabilitySeverity.CRITICAL,
    ),
    CapabilityDefinition(
        key="burn",
        label="Burn",
        category="token_control",
        selectors=BURN_SELECTORS,
        function_names=frozenset({"burn", "burnfrom", "_burn"}),
        access_control_role="BURNER_ROLE",
        default_severity=CapabilitySeverity.MEDIUM,
    ),
    CapabilityDefinition(
        key="pause",
        label="Pause",
        category="token_control",
        selectors=frozenset(bytes.fromhex(s) for s in ("8456cb59", "3f4ba83a")),
        function_names=frozenset({"pause", "unpause"}),
        access_control_role="PAUSER_ROLE",
        default_severity=CapabilitySeverity.HIGH,
    ),
    CapabilityDefinition(
        key="blacklist",
        label="Blacklist",
        category="token_control",
        selectors=BLACKLIST_PROBE_SELECTORS,
        function_names=frozenset(
            {
                "blacklist",
                "addtoblacklist",
                "setblacklist",
                "blocklist",
                "isblacklisted",
            }
        ),
        access_control_role=None,
        default_severity=CapabilitySeverity.CRITICAL,
    ),
    CapabilityDefinition(
        key="whitelist",
        label="Whitelist",
        category="token_control",
        selectors=WHITELIST_SELECTORS,
        function_names=frozenset({"addtowhitelist", "whitelist", "iswhitelisted"}),
        access_control_role=None,
        default_severity=CapabilitySeverity.MEDIUM,
    ),
    CapabilityDefinition(
        key="freeze",
        label="Freeze",
        category="token_control",
        selectors=FREEZE_SELECTORS,
        function_names=frozenset({"freeze", "unfreeze", "freezeaccount"}),
        access_control_role=None,
        default_severity=CapabilitySeverity.HIGH,
    ),
    CapabilityDefinition(
        key="seize",
        label="Seize",
        category="token_control",
        selectors=SEIZE_SELECTORS,
        function_names=frozenset({"seize", "confiscate", "seizefunds"}),
        access_control_role=None,
        default_severity=CapabilitySeverity.CRITICAL,
    ),
    CapabilityDefinition(
        key="trading_gate",
        label="Trading Gate",
        category="trading_control",
        selectors=TRADING_ENABLED_SELECTORS,
        function_names=frozenset(
            {"enabletrading", "settradingenabled", "opentrading", "launch"}
        ),
        access_control_role=None,
        default_severity=CapabilitySeverity.HIGH,
    ),
    CapabilityDefinition(
        key="max_wallet",
        label="Max Wallet",
        category="trading_control",
        selectors=frozenset({bytes.fromhex("5d0044ca")}),
        function_names=frozenset({"setmaxwallet", "maxwallet"}),
        access_control_role=None,
        default_severity=CapabilitySeverity.MEDIUM,
    ),
    CapabilityDefinition(
        key="max_transaction",
        label="Max Transaction",
        category="trading_control",
        selectors=frozenset({bytes.fromhex("ec28438a"), bytes.fromhex("e99c9d09")}),
        function_names=frozenset({"setmaxtxamount", "setmaxsellamount"}),
        access_control_role=None,
        default_severity=CapabilitySeverity.MEDIUM,
    ),
    CapabilityDefinition(
        key="cooldown",
        label="Cooldown",
        category="trading_control",
        selectors=COOLDOWN_SELECTORS,
        function_names=frozenset({"setcooldownenabled", "settransferdelay"}),
        access_control_role=None,
        default_severity=CapabilitySeverity.LOW,
    ),
    CapabilityDefinition(
        key="anti_bot",
        label="Anti-Bot",
        category="trading_control",
        selectors=frozenset({bytes.fromhex("9c0db5f3"), bytes.fromhex("3bbac579")}),
        function_names=frozenset({"setbots", "isbot", "antibot"}),
        access_control_role=None,
        default_severity=CapabilitySeverity.MEDIUM,
    ),
    CapabilityDefinition(
        key="buy_tax",
        label="Buy Tax",
        category="fee_logic",
        selectors=frozenset(
            {bytes.fromhex("0cc835a3"), bytes.fromhex("47062402"), bytes.fromhex("0b78f9c0")}
        ),
        function_names=frozenset({"setbuyfee", "buyfee", "setfees"}),
        access_control_role=None,
        default_severity=CapabilitySeverity.MEDIUM,
    ),
    CapabilityDefinition(
        key="sell_tax",
        label="Sell Tax",
        category="fee_logic",
        selectors=frozenset(
            {bytes.fromhex("8b4cee08"), bytes.fromhex("2b14ca56"), bytes.fromhex("0b78f9c0")}
        ),
        function_names=frozenset({"setsellfee", "sellfee", "setfees"}),
        access_control_role=None,
        default_severity=CapabilitySeverity.HIGH,
    ),
    CapabilityDefinition(
        key="dynamic_tax",
        label="Dynamic Tax",
        category="fee_logic",
        selectors=frozenset(
            {
                bytes.fromhex("6db79437"),
                bytes.fromhex("ec1f3f63"),
                bytes.fromhex("c4081a4c"),
            }
        ),
        function_names=frozenset({"updatefees", "reducefee", "settaxfee"}),
        access_control_role=None,
        default_severity=CapabilitySeverity.HIGH,
    ),
    CapabilityDefinition(
        key="treasury_fee",
        label="Treasury Fee",
        category="fee_logic",
        selectors=TRANSFER_TAX_SELECTORS,
        function_names=frozenset({"settaxfee", "treasury", "settreasury"}),
        access_control_role=None,
        default_severity=CapabilitySeverity.MEDIUM,
    ),
    CapabilityDefinition(
        key="fee_exemption",
        label="Fee Exemption",
        category="fee_logic",
        selectors=frozenset({bytes.fromhex("5342acb4")}),
        function_names=frozenset({"isexcludedfromfee", "excludefromfee"}),
        access_control_role=None,
        default_severity=CapabilitySeverity.LOW,
    ),
    CapabilityDefinition(
        key="transfer_ownership",
        label="Transfer Ownership",
        category="governance_hooks",
        selectors=frozenset({bytes.fromhex("f2fde38b"), bytes.fromhex("8da5cb5b")}),
        function_names=frozenset({"transferownership", "owner"}),
        access_control_role="DEFAULT_ADMIN_ROLE",
        default_severity=CapabilitySeverity.HIGH,
    ),
    CapabilityDefinition(
        key="renounce_ownership",
        label="Renounce Ownership",
        category="governance_hooks",
        selectors=frozenset({bytes.fromhex("715018a6")}),
        function_names=frozenset({"renounceownership"}),
        access_control_role="DEFAULT_ADMIN_ROLE",
        default_severity=CapabilitySeverity.MEDIUM,
    ),
    CapabilityDefinition(
        key="grant_role",
        label="Grant Role",
        category="governance_hooks",
        selectors=frozenset({GRANT_ROLE_SELECTOR}),
        function_names=frozenset({"grantrole"}),
        access_control_role="DEFAULT_ADMIN_ROLE",
        default_severity=CapabilitySeverity.HIGH,
    ),
    CapabilityDefinition(
        key="revoke_role",
        label="Revoke Role",
        category="governance_hooks",
        selectors=frozenset({REVOKE_ROLE_SELECTOR}),
        function_names=frozenset({"revokerole"}),
        access_control_role="DEFAULT_ADMIN_ROLE",
        default_severity=CapabilitySeverity.MEDIUM,
    ),
)

CAPABILITY_KEYS: frozenset[str] = frozenset(defn.key for defn in CAPABILITY_CATALOG)
