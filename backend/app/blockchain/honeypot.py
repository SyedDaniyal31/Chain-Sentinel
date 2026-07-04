"""Honeypot and trading-restriction fingerprints for bytecode and ABI analysis."""

from dataclasses import dataclass

# Admin-controlled trading launch / gate functions.
TRADING_ENABLED_SELECTORS: frozenset[bytes] = frozenset(
    bytes.fromhex(selector)
    for selector in (
        "8a8c523c",  # enableTrading()
        "c2e5ec04",  # setTradingEnabled(bool)
        "4ada218b",  # tradingEnabled()
        "c9567bf9",  # openTrading()
        "01339c21",  # launch()
    )
)

WHITELIST_SELECTORS: frozenset[bytes] = frozenset(
    bytes.fromhex(selector)
    for selector in (
        "e43252d7",  # addToWhitelist(address)
        "9b19251a",  # whitelist(address)
        "3af32abf",  # isWhitelisted(address)
        "53d6fd59",  # setWhitelist(address,bool)
    )
)

BLACKLIST_PROBE_SELECTORS: frozenset[bytes] = frozenset(
    bytes.fromhex(selector)
    for selector in (
        "fe575a87",  # isBlacklisted(address)
        "3bbac579",  # isBot(address)
        "9c0db5f3",  # setBots(address[],bool)
        "f9f92be4",  # blacklist(address)
        "44337ea1",  # addToBlacklist(address)
    )
)

SELL_RESTRICTION_SELECTORS: frozenset[bytes] = frozenset(
    bytes.fromhex(selector)
    for selector in (
        "e99c9d09",  # setMaxSellAmount(uint256)
        "ec28438a",  # setMaxTxAmount(uint256)
        "5d0044ca",  # setMaxWallet(uint256)
        "9c0db5f3",  # setBots(address[],bool)
    )
)

TRANSFER_TAX_SELECTORS: frozenset[bytes] = frozenset(
    bytes.fromhex(selector)
    for selector in (
        "c4081a4c",  # setTaxFee(uint256)
        "8b4cee08",  # setSellFee(uint256)
        "0cc835a3",  # setBuyFee(uint256)
        "0b78f9c0",  # setFees(uint256,uint256)
        "6db79437",  # updateFees(uint256,uint256)
        "ec1f3f63",  # reduceFee(uint256)
        "69fe0e2d",  # setFee(uint256)
        "2b14ca56",  # sellFee()
        "47062402",  # buyFee()
        "5342acb4",  # isExcludedFromFee(address)
    )
)

TRADING_ENABLED_FUNCTION_NAMES: frozenset[str] = frozenset(
    name.lower()
    for name in (
        "enableTrading",
        "setTradingEnabled",
        "tradingEnabled",
        "openTrading",
        "launch",
        "startTrading",
    )
)

WHITELIST_FUNCTION_NAMES: frozenset[str] = frozenset(
    name.lower()
    for name in (
        "addToWhitelist",
        "whitelist",
        "isWhitelisted",
        "setWhitelist",
        "removeFromWhitelist",
    )
)

BLACKLIST_PROBE_FUNCTION_NAMES: frozenset[str] = frozenset(
    name.lower()
    for name in (
        "isBlacklisted",
        "isBot",
        "setBots",
        "blacklist",
        "addToBlacklist",
        "isBlocked",
    )
)

SELL_RESTRICTION_FUNCTION_NAMES: frozenset[str] = frozenset(
    name.lower()
    for name in (
        "setMaxSellAmount",
        "setMaxTxAmount",
        "setMaxWallet",
        "maxSellTransactionAmount",
        "cannotSell",
        "isSellBlocked",
    )
)

TRANSFER_TAX_FUNCTION_NAMES: frozenset[str] = frozenset(
    name.lower()
    for name in (
        "setTaxFee",
        "setSellFee",
        "setBuyFee",
        "setFees",
        "updateFees",
        "reduceFee",
        "setFee",
        "sellFee",
        "buyFee",
        "isExcludedFromFee",
        "setCustomTax",
    )
)


@dataclass(frozen=True, slots=True)
class HoneypotFlags:
    """Normalized honeypot / trading-restriction indicators."""

    trading_enabled_control: bool = False
    whitelist_control: bool = False
    blacklist_sell_blocking: bool = False
    transfer_tax_control: bool = False

    @property
    def has_any(self) -> bool:
        return (
            self.trading_enabled_control
            or self.whitelist_control
            or self.blacklist_sell_blocking
            or self.transfer_tax_control
        )


def detect_honeypot_from_bytecode(bytecode: bytes) -> HoneypotFlags:
    """Scan runtime bytecode for honeypot and trading-restriction selectors."""
    if not bytecode:
        return HoneypotFlags()

    has_blacklist_probe = _bytecode_has_any_selector(bytecode, BLACKLIST_PROBE_SELECTORS)
    has_sell_restriction = _bytecode_has_any_selector(bytecode, SELL_RESTRICTION_SELECTORS)

    return HoneypotFlags(
        trading_enabled_control=_bytecode_has_any_selector(bytecode, TRADING_ENABLED_SELECTORS),
        whitelist_control=_bytecode_has_any_selector(bytecode, WHITELIST_SELECTORS),
        blacklist_sell_blocking=has_blacklist_probe and has_sell_restriction,
        transfer_tax_control=_bytecode_has_any_selector(bytecode, TRANSFER_TAX_SELECTORS),
    )


def detect_honeypot_from_abi(abi: list[dict[str, object]]) -> HoneypotFlags:
    """Parse a verified contract ABI for honeypot-related function surfaces."""
    function_names = _abi_function_names(abi)
    return _flags_from_function_names(function_names)


def detect_honeypot_from_source(source_code: str) -> HoneypotFlags:
    """Fallback parser for verified Solidity when ABI JSON is unavailable."""
    import re

    matches = re.findall(r"function\s+(\w+)\s*\(", source_code)
    return _flags_from_function_names(name.lower() for name in matches)


def merge_honeypot_flags(*flag_sets: HoneypotFlags) -> HoneypotFlags:
    """Combine heuristic and simulation findings (simulation overrides blocking)."""
    trading = any(flags.trading_enabled_control for flags in flag_sets)
    whitelist = any(flags.whitelist_control for flags in flag_sets)
    blacklist_sell = any(flags.blacklist_sell_blocking for flags in flag_sets)
    transfer_tax = any(flags.transfer_tax_control for flags in flag_sets)
    return HoneypotFlags(
        trading_enabled_control=trading,
        whitelist_control=whitelist,
        blacklist_sell_blocking=blacklist_sell,
        transfer_tax_control=transfer_tax,
    )


def _bytecode_has_any_selector(bytecode: bytes, selectors: frozenset[bytes]) -> bool:
    return any(selector in bytecode for selector in selectors)


def _abi_function_names(abi: list[dict[str, object]]) -> set[str]:
    names: set[str] = set()
    for entry in abi:
        if entry.get("type") != "function":
            continue
        name = entry.get("name")
        if isinstance(name, str):
            names.add(name.lower())
    return names


def _flags_from_function_names(function_names: set[str] | frozenset[str]) -> HoneypotFlags:
    names = set(function_names)
    has_blacklist_probe = bool(names & BLACKLIST_PROBE_FUNCTION_NAMES)
    has_sell_restriction = bool(names & SELL_RESTRICTION_FUNCTION_NAMES)
    return HoneypotFlags(
        trading_enabled_control=bool(names & TRADING_ENABLED_FUNCTION_NAMES),
        whitelist_control=bool(names & WHITELIST_FUNCTION_NAMES),
        blacklist_sell_blocking=has_blacklist_probe and has_sell_restriction,
        transfer_tax_control=bool(names & TRANSFER_TAX_FUNCTION_NAMES),
    )
