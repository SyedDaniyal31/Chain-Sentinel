"""Oracle protocol detection for M6.1 DeFi protocol intelligence."""

from __future__ import annotations

from dataclasses import dataclass

from app.blockchain.protocol.defi_registry import source_contains_marker
from app.blockchain.protocol.models import OracleDetectionResult, ProtocolDetectionContext

CHAINLINK_LATEST_ANSWER = bytes.fromhex("50d25bcd")
CHAINLINK_LATEST_ROUND = bytes.fromhex("feaf968c")
CHAINLINK_DESCRIPTION = bytes.fromhex("7284e416")

PYTH_GET_PRICE = bytes.fromhex("9d15dcc8")
PYTH_GET_PRICE_NO_AGE = bytes.fromhex("6cc43823")

REDSTONE_GET_DATA = bytes.fromhex("3b8745f9")
REDSTONE_GET_VALUE = bytes.fromhex("d1bd83d9")


@dataclass(frozen=True, slots=True)
class OracleSignatureProfile:
    name: str
    selectors: tuple[bytes, ...]
    source_markers: tuple[str, ...]


ORACLE_SIGNATURE_PROFILES: tuple[OracleSignatureProfile, ...] = (
    OracleSignatureProfile(
        name="Chainlink",
        selectors=(CHAINLINK_LATEST_ANSWER, CHAINLINK_LATEST_ROUND, CHAINLINK_DESCRIPTION),
        source_markers=("CHAINLINK", "AGGREGATORV3", "PRICE FEED"),
    ),
    OracleSignatureProfile(
        name="Pyth",
        selectors=(PYTH_GET_PRICE, PYTH_GET_PRICE_NO_AGE),
        source_markers=("PYTH", "IPYTH", "PYTHNETWORK"),
    ),
    OracleSignatureProfile(
        name="Redstone",
        selectors=(REDSTONE_GET_DATA, REDSTONE_GET_VALUE),
        source_markers=("REDSTONE", "REDSTONEORACLE", "DATAFEED"),
    ),
)


def detect_oracles(context: ProtocolDetectionContext) -> list[OracleDetectionResult]:
    """Detect oracle integrations from bytecode and verified source markers."""
    if not context.bytecode and not context.logic_bytecode:
        return []

    results: dict[str, OracleDetectionResult] = {}
    bytecode = context.logic_bytecode or context.bytecode

    for profile in ORACLE_SIGNATURE_PROFILES:
        selector_hits = sum(1 for selector in profile.selectors if selector in bytecode)
        if selector_hits == 0 and not source_contains_marker(
            context.verified_source_code,
            profile.source_markers,
        ):
            continue

        source_boost = 15 if source_contains_marker(context.verified_source_code, profile.source_markers) else 0
        verified_boost = 5 if context.is_verified and source_boost == 0 else 0
        selector_score = selector_hits * 20
        score = min(100, 35 + selector_score + source_boost + verified_boost)

        existing = results.get(profile.name)
        candidate = OracleDetectionResult(name=profile.name, confidence=score)
        if existing is None or candidate.confidence > existing.confidence:
            results[profile.name] = candidate

    return sorted(results.values(), key=lambda item: item.confidence, reverse=True)
