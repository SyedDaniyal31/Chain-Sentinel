"""Static wallet reputation provider with known denylist entries (M5.2)."""

from __future__ import annotations

from app.blockchain.wallet.reputation_provider import WalletReputationProvider, WalletReputationResult
from app.models.enums import ConfidenceLevel

KNOWN_SCAM_ADDRESSES: frozenset[str] = frozenset(
    address.lower()
    for address in (
        "0x8589427373d6d57e722938443819027f913358bb",
        "0xd90e2f925ba723939877147291111569bc6c9620",
        "0x722122dfeb585d0a4c494276170a0f9620b2e470",
    )
)

PHISHING_ADDRESSES: frozenset[str] = frozenset()

SANCTIONED_ADDRESSES: frozenset[str] = frozenset(
    address.lower()
    for address in (
        "0x8589427373d6d57e722938443819027f913358bb",
        "0xd90e2f925ba723939877147291111569bc6c9620",
        "0x722122dfeb585d0a4c494276170a0f9620b2e470",
        "0x12d66f87a04a9e220743712ce6d9bb1b5616b8fc",
    )
)

EXPLOIT_RELATED_ADDRESSES: frozenset[str] = frozenset(
    address.lower()
    for address in (
        "0x8589427373d6d57e722938443819027f913358bb",
    )
)


class StaticWalletReputationProvider(WalletReputationProvider):
    """In-memory denylist provider suitable for tests and offline scans."""

    async def lookup(self, wallet_address: str, chain_id: int) -> WalletReputationResult:
        normalized = wallet_address.lower()
        known_scam = normalized in KNOWN_SCAM_ADDRESSES
        phishing = normalized in PHISHING_ADDRESSES
        sanctioned = normalized in SANCTIONED_ADDRESSES
        exploit_related = normalized in EXPLOIT_RELATED_ADDRESSES

        if not any((known_scam, phishing, sanctioned, exploit_related)):
            return WalletReputationResult()

        confidence = ConfidenceLevel.HIGH if sanctioned else ConfidenceLevel.MEDIUM
        return WalletReputationResult(
            known_scam=known_scam,
            phishing=phishing,
            sanctioned=sanctioned,
            exploit_related=exploit_related,
            confidence=confidence,
        )
