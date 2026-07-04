"""Wallet reputation provider abstractions for M5.2."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.models.enums import ConfidenceLevel


@dataclass(frozen=True, slots=True)
class WalletReputationResult:
    """Reputation flags for a wallet address."""

    known_scam: bool = False
    phishing: bool = False
    sanctioned: bool = False
    exploit_related: bool = False
    confidence: ConfidenceLevel = ConfidenceLevel.LOW


class WalletReputationProvider(ABC):
    """Resolve wallet reputation from external or static intelligence sources."""

    @abstractmethod
    async def lookup(self, wallet_address: str, chain_id: int) -> WalletReputationResult:
        """Return reputation flags for the given wallet."""
