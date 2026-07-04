"""Lending protocol detection for M6.1 DeFi protocol intelligence."""

from __future__ import annotations

from dataclasses import dataclass

from app.blockchain.protocol.defi_registry import match_deployments, source_contains_marker
from app.blockchain.protocol.models import LendingDetectionResult, ProtocolDetectionContext

AAVE_SUPPLY = bytes.fromhex("617ba037")
AAVE_BORROW = bytes.fromhex("a415143d")
AAVE_GET_RESERVE_DATA = bytes.fromhex("35ea6a75")

COMPOUND_MINT = bytes.fromhex("a0712d68")
COMPOUND_REDEEM = bytes.fromhex("db006a75")
COMPOUND_EXCHANGE_RATE = bytes.fromhex("182df0f5")

MORPHO_SUPPLY = bytes.fromhex("a0712d68")
MORPHO_MARKET = bytes.fromhex("5c38449e")

SPARK_SUPPLY = bytes.fromhex("617ba037")
SPARK_BORROW = bytes.fromhex("a415143d")


@dataclass(frozen=True, slots=True)
class LendingSignatureProfile:
    name: str
    role: str
    selectors: tuple[bytes, ...]
    source_markers: tuple[str, ...]


LENDING_SIGNATURE_PROFILES: tuple[LendingSignatureProfile, ...] = (
    LendingSignatureProfile(
        name="Aave",
        role="pool",
        selectors=(AAVE_SUPPLY, AAVE_BORROW, AAVE_GET_RESERVE_DATA),
        source_markers=("AAVE", "LENDINGPOOL", "IPOOL"),
    ),
    LendingSignatureProfile(
        name="Compound",
        role="market",
        selectors=(COMPOUND_MINT, COMPOUND_REDEEM, COMPOUND_EXCHANGE_RATE),
        source_markers=("COMPOUND", "CEToken", "COMPTROLLER"),
    ),
    LendingSignatureProfile(
        name="Morpho",
        role="market",
        selectors=(MORPHO_SUPPLY, MORPHO_MARKET),
        source_markers=("MORPHO", "IMORPHO", "MORPHOBASE"),
    ),
    LendingSignatureProfile(
        name="Spark",
        role="pool",
        selectors=(SPARK_SUPPLY, SPARK_BORROW, AAVE_GET_RESERVE_DATA),
        source_markers=("SPARK", "SPARKLEND", "LENDINGPOOL"),
    ),
)


def detect_lending(context: ProtocolDetectionContext) -> list[LendingDetectionResult]:
    """Detect lending protocol integrations from registry, bytecode, and source."""
    if not context.bytecode and not context.logic_bytecode:
        return []

    results: dict[tuple[str, str], LendingDetectionResult] = {}
    bytecode = context.logic_bytecode or context.bytecode

    for deployment in match_deployments(context.chain_id, context.target_address):
        if deployment.protocol in {"Aave", "Compound", "Spark", "Morpho"}:
            _upsert_result(
                results,
                LendingDetectionResult(
                    name=deployment.protocol,
                    role=deployment.role,
                    confidence=95,
                ),
            )

    for profile in LENDING_SIGNATURE_PROFILES:
        selector_hits = sum(1 for selector in profile.selectors if selector in bytecode)
        if selector_hits == 0:
            continue

        source_boost = 12 if source_contains_marker(context.verified_source_code, profile.source_markers) else 0
        verified_boost = 5 if context.is_verified and source_boost == 0 else 0
        score = min(100, 40 + selector_hits * 18 + source_boost + verified_boost)

        _upsert_result(
            results,
            LendingDetectionResult(name=profile.name, role=profile.role, confidence=score),
        )

    return sorted(results.values(), key=lambda item: item.confidence, reverse=True)


def _upsert_result(
    results: dict[tuple[str, str], LendingDetectionResult],
    candidate: LendingDetectionResult,
) -> None:
    key = (candidate.name, candidate.role)
    existing = results.get(key)
    if existing is None or candidate.confidence > existing.confidence:
        results[key] = candidate
