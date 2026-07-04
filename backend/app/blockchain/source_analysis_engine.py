"""M4.2 source-code pattern analysis for governance, capability, and honeypot signals."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.blockchain.contract_source_provider import VerifiedContractSource
from app.models.enums import ConfidenceLevel

ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"


@dataclass(frozen=True, slots=True)
class SourcePatternHit:
    """Result of a single source-level pattern probe."""

    detected: bool
    confidence: ConfidenceLevel = ConfidenceLevel.LOW
    evidence: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class SourceAnalysisResult:
    """Aggregate verified-source intelligence used by downstream analyzers."""

    verified: bool
    ownable: SourcePatternHit = field(default_factory=lambda: SourcePatternHit(False))
    access_control: SourcePatternHit = field(default_factory=lambda: SourcePatternHit(False))
    pausable: SourcePatternHit = field(default_factory=lambda: SourcePatternHit(False))
    blacklist: SourcePatternHit = field(default_factory=lambda: SourcePatternHit(False))
    trading_gate: SourcePatternHit = field(default_factory=lambda: SourcePatternHit(False))
    tax_controller: SourcePatternHit = field(default_factory=lambda: SourcePatternHit(False))
    rescue_function: SourcePatternHit = field(default_factory=lambda: SourcePatternHit(False))
    renounced_ownership: bool = False
    role_names: frozenset[str] = frozenset()
    abi_function_names: frozenset[str] = frozenset()
    source_confidence: ConfidenceLevel = ConfidenceLevel.LOW

    @property
    def function_names(self) -> set[str]:
        return set(self.abi_function_names)


_OWNABLE_MARKERS = (
    r"\bOwnable\b",
    r"\bOwnable2Step\b",
    r"function\s+owner\s*\(",
    r"function\s+transferOwnership\s*\(",
    r"function\s+renounceOwnership\s*\(",
)

_ACCESS_CONTROL_MARKERS = (
    r"\bAccessControl\b",
    r"\bAccessControlEnumerable\b",
    r"DEFAULT_ADMIN_ROLE",
    r"function\s+grantRole\s*\(",
    r"function\s+revokeRole\s*\(",
    r"function\s+hasRole\s*\(",
    r"function\s+getRoleAdmin\s*\(",
)

_PAUSABLE_MARKERS = (
    r"\bPausable\b",
    r"function\s+pause\s*\(",
    r"function\s+unpause\s*\(",
    r"whenNotPaused",
    r"whenPaused",
)

_BLACKLIST_MARKERS = (
    r"blacklist",
    r"blocklist",
    r"isBlacklisted",
    r"isBot",
    r"setBots",
    r"addToBlacklist",
)

_TRADING_GATE_MARKERS = (
    r"enableTrading",
    r"setTradingEnabled",
    r"openTrading",
    r"startTrading",
    r"launch\s*\(",
    r"tradingEnabled",
)

_TAX_CONTROLLER_MARKERS = (
    r"setTaxFee",
    r"setBuyFee",
    r"setSellFee",
    r"setFees",
    r"updateFees",
    r"reduceFee",
    r"setCustomTax",
    r"buyFee",
    r"sellFee",
    r"isExcludedFromFee",
)

_RESCUE_MARKERS = (
    r"rescueTokens",
    r"rescueETH",
    r"recoverERC20",
    r"recoverTokens",
    r"sweep",
    r"withdrawStuck",
    r"claimStuckTokens",
)

_ABI_OWNABLE = frozenset({"owner", "transferownership", "renounceownership"})
_ABI_ACCESS_CONTROL = frozenset({"grantrole", "revokerole", "hasrole", "getroleadmin"})
_ABI_PAUSABLE = frozenset({"pause", "unpause"})
_ABI_BLACKLIST = frozenset(
    {"blacklist", "addtoblacklist", "isblacklisted", "isbot", "setbots"}
)
_ABI_TRADING_GATE = frozenset(
    {"enabletrading", "settradingenabled", "opentrading", "starttrading", "launch"}
)
_ABI_TAX = frozenset(
    {"settaxfee", "setbuyfee", "setsellfee", "setfees", "updatefees", "reducefee", "setfee"}
)
_ABI_RESCUE = frozenset(
    {"rescuetokens", "rescueeth", "recovererc20", "recovertokens", "sweep"}
)


class SourceAnalysisEngine:
    """Analyze verified explorer source + ABI for high-confidence security patterns."""

    def analyze(
        self,
        verified: VerifiedContractSource | None,
        *,
        ownership_address: str | None = None,
    ) -> SourceAnalysisResult | None:
        if verified is None or not verified.is_verified:
            return None

        source = verified.source_code
        abi_names = _abi_function_names(verified.abi)
        role_names = _extract_role_names(source)

        ownable = _detect_pattern(
            source,
            abi_names,
            markers=_OWNABLE_MARKERS,
            abi_markers=_ABI_OWNABLE,
        )
        access_control = _detect_pattern(
            source,
            abi_names,
            markers=_ACCESS_CONTROL_MARKERS,
            abi_markers=_ABI_ACCESS_CONTROL,
            extra_evidence=tuple(sorted(role_names)) if role_names else (),
        )
        pausable = _detect_pattern(
            source,
            abi_names,
            markers=_PAUSABLE_MARKERS,
            abi_markers=_ABI_PAUSABLE,
        )
        blacklist = _detect_pattern(
            source,
            abi_names,
            markers=_BLACKLIST_MARKERS,
            abi_markers=_ABI_BLACKLIST,
        )
        trading_gate = _detect_pattern(
            source,
            abi_names,
            markers=_TRADING_GATE_MARKERS,
            abi_markers=_ABI_TRADING_GATE,
        )
        tax_controller = _detect_pattern(
            source,
            abi_names,
            markers=_TAX_CONTROLLER_MARKERS,
            abi_markers=_ABI_TAX,
        )
        rescue_function = _detect_pattern(
            source,
            abi_names,
            markers=_RESCUE_MARKERS,
            abi_markers=_ABI_RESCUE,
        )

        renounced = _detect_renounced_ownership(
            source,
            abi_names,
            ownership_address=ownership_address,
        )

        return SourceAnalysisResult(
            verified=True,
            ownable=ownable,
            access_control=access_control,
            pausable=pausable,
            blacklist=blacklist,
            trading_gate=trading_gate,
            tax_controller=tax_controller,
            rescue_function=rescue_function,
            renounced_ownership=renounced,
            role_names=role_names,
            abi_function_names=frozenset(name.lower() for name in abi_names),
            source_confidence=ConfidenceLevel.HIGH,
        )


def merge_abi_function_names(
    source_analysis: SourceAnalysisResult | None,
    fallback: set[str] | None,
) -> set[str] | None:
    if source_analysis is not None:
        return source_analysis.function_names
    return fallback


def _detect_pattern(
    source: str,
    function_names: set[str],
    *,
    markers: tuple[str, ...],
    abi_markers: frozenset[str],
    extra_evidence: tuple[str, ...] = (),
) -> SourcePatternHit:
    evidence: list[str] = []
    source_hit = False
    for marker in markers:
        if re.search(marker, source, flags=re.IGNORECASE):
            source_hit = True
            evidence.append(f"source:{marker.strip(chr(92))}")

    normalized_abi = {name.lower() for name in function_names}
    abi_hit = bool(normalized_abi & abi_markers)
    if abi_hit:
        matched = sorted(normalized_abi & abi_markers)
        evidence.extend(f"abi:{name}()" for name in matched)

    evidence.extend(extra_evidence)
    detected = source_hit or abi_hit
    confidence = ConfidenceLevel.HIGH if detected else ConfidenceLevel.LOW
    return SourcePatternHit(detected=detected, confidence=confidence, evidence=tuple(evidence))


def _detect_renounced_ownership(
    source: str,
    abi_names: set[str],
    *,
    ownership_address: str | None,
) -> bool:
    if ownership_address is not None and ownership_address.lower() == ZERO_ADDRESS:
        return True

    normalized = {name.lower() for name in abi_names}
    has_renounce = "renounceownership" in normalized or re.search(
        r"function\s+renounceOwnership\s*\(",
        source,
        flags=re.IGNORECASE,
    )
    if not has_renounce:
        return False

    return ownership_address is None or ownership_address.lower() == ZERO_ADDRESS


def _abi_function_names(abi: list[dict[str, object]] | None) -> set[str]:
    if not abi:
        return set()
    names: set[str] = set()
    for entry in abi:
        if entry.get("type") != "function":
            continue
        name = entry.get("name")
        if isinstance(name, str):
            names.add(name)
    return names


def _extract_role_names(source: str) -> frozenset[str]:
    roles = set(re.findall(r"(?:bytes32\s+(?:public\s+|constant\s+)?)?([A-Z][A-Z0-9_]*_ROLE)\b", source))
    if "DEFAULT_ADMIN_ROLE" not in roles and "AccessControl" in source:
        roles.add("DEFAULT_ADMIN_ROLE")
    return frozenset(roles)
