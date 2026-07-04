"""Dangerous contract capability fingerprints for bytecode and ABI analysis."""

from dataclasses import dataclass

# Function selectors grouped by capability (keccak256(signature)[:4]).
MINT_SELECTORS: frozenset[bytes] = frozenset(
    bytes.fromhex(selector)
    for selector in (
        "40c10f19",  # mint(address,uint256)
        "a0712d68",  # mint(uint256)
        "6a627842",  # mint(address)
        "449a52f8",  # mintTo(address,uint256)
    )
)

PAUSE_SELECTORS: frozenset[bytes] = frozenset(
    bytes.fromhex(selector)
    for selector in (
        "8456cb59",  # pause()
        "3f4ba83a",  # unpause()
    )
)

BLACKLIST_SELECTORS: frozenset[bytes] = frozenset(
    bytes.fromhex(selector)
    for selector in (
        "f9f92be4",  # blacklist(address)
        "44337ea1",  # addToBlacklist(address)
        "153b0d1e",  # setBlacklist(address,bool)
        "e5c7160b",  # blocklist(address)
        "fe575a87",  # isBlacklisted(address)
    )
)

OWNERSHIP_SELECTORS: frozenset[bytes] = frozenset(
    bytes.fromhex(selector)
    for selector in (
        "8da5cb5b",  # owner()
        "f2fde38b",  # transferOwnership(address)
        "715018a6",  # renounceOwnership()
    )
)

MINT_FUNCTION_NAMES: frozenset[str] = frozenset(
    name.lower()
    for name in ("mint", "mintTo", "_mint")
)

PAUSE_FUNCTION_NAMES: frozenset[str] = frozenset(
    name.lower()
    for name in ("pause",)
)

BLACKLIST_FUNCTION_NAMES: frozenset[str] = frozenset(
    name.lower()
    for name in (
        "blacklist",
        "addToBlacklist",
        "setBlacklist",
        "blocklist",
        "addToBlocklist",
        "ban",
        "addToDenylist",
    )
)

OWNERSHIP_FUNCTION_NAMES: frozenset[str] = frozenset(
    name.lower()
    for name in ("owner", "transferOwnership", "renounceOwnership")
)


@dataclass(frozen=True, slots=True)
class CapabilityFlags:
    """Normalized dangerous-capability booleans."""

    mint_capability: bool = False
    pause_capability: bool = False
    blacklist_capability: bool = False
    ownership_capability: bool = False

    @property
    def has_any(self) -> bool:
        return (
            self.mint_capability
            or self.pause_capability
            or self.blacklist_capability
            or self.ownership_capability
        )


def detect_capabilities_from_bytecode(bytecode: bytes) -> CapabilityFlags:
    """
    Scan runtime bytecode for known dangerous function selectors.

    Heuristic-only: proxies may hide logic; unverified custom names are missed.
    """
    if not bytecode:
        return CapabilityFlags()

    return CapabilityFlags(
        mint_capability=_bytecode_has_any_selector(bytecode, MINT_SELECTORS),
        pause_capability=_bytecode_has_any_selector(bytecode, PAUSE_SELECTORS),
        blacklist_capability=_bytecode_has_any_selector(bytecode, BLACKLIST_SELECTORS),
        ownership_capability=_bytecode_has_any_selector(bytecode, OWNERSHIP_SELECTORS),
    )


def detect_capabilities_from_abi(abi: list[dict[str, object]]) -> CapabilityFlags:
    """Parse a verified contract ABI for externally visible dangerous functions."""
    function_names = _abi_function_names(abi)
    return _flags_from_function_names(function_names)


def detect_capabilities_from_source(source_code: str) -> CapabilityFlags:
    """
    Fallback parser for verified Solidity when ABI JSON is unavailable.

    Uses conservative function-name matching — prefer ABI parsing when possible.
    """
    import re

    matches = re.findall(r"function\s+(\w+)\s*\(", source_code)
    return _flags_from_function_names(name.lower() for name in matches)


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


def _flags_from_function_names(function_names: set[str] | frozenset[str]) -> CapabilityFlags:
    names = set(function_names)
    return CapabilityFlags(
        mint_capability=bool(names & MINT_FUNCTION_NAMES),
        pause_capability=bool(names & PAUSE_FUNCTION_NAMES),
        blacklist_capability=bool(names & BLACKLIST_FUNCTION_NAMES),
        ownership_capability=bool(names & OWNERSHIP_FUNCTION_NAMES),
    )
