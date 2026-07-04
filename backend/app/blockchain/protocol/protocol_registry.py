"""Known protocol integration registry for M6.0."""

from __future__ import annotations

from dataclasses import dataclass

from app.blockchain.multisig import GET_OWNERS_SELECTOR, GET_THRESHOLD_SELECTOR


@dataclass(frozen=True, slots=True)
class ProtocolIntegrationProfile:
    """Known third-party protocol integration fingerprint."""

    name: str
    selectors: tuple[bytes, ...]
    description: str


INTEGRATION_PROFILES: tuple[ProtocolIntegrationProfile, ...] = (
    ProtocolIntegrationProfile(
        name="Uniswap V2 Pair",
        selectors=(
            bytes.fromhex("0902f1ac"),
            bytes.fromhex("022c0d9f"),
        ),
        description="Uniswap V2-style AMM pair interface",
    ),
    ProtocolIntegrationProfile(
        name="Chainlink Aggregator",
        selectors=(
            bytes.fromhex("50d25bcd"),
            bytes.fromhex("feaf968c"),
        ),
        description="Chainlink price feed aggregator interface",
    ),
    ProtocolIntegrationProfile(
        name="Gnosis Safe",
        selectors=(
            GET_OWNERS_SELECTOR,
            GET_THRESHOLD_SELECTOR,
        ),
        description="Gnosis Safe multisig wallet interface",
    ),
)


def detect_integrations(bytecode: bytes) -> list[str]:
    """Return human-readable integration labels matched in bytecode."""
    if not bytecode:
        return []

    matches: list[str] = []
    for profile in INTEGRATION_PROFILES:
        if all(selector in bytecode for selector in profile.selectors):
            matches.append(profile.name)
    return matches
