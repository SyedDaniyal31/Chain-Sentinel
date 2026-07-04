"""Wallet history provider abstractions for M5.2."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ExplorerTransaction:
    """Normalized explorer transaction record."""

    hash: str
    from_address: str
    to_address: str | None
    value_wei: int
    block_number: int
    timestamp: int
    is_error: bool = False


class WalletHistoryProvider(ABC):
    """Fetch wallet and contract transaction history from a block explorer."""

    @abstractmethod
    async def get_contract_creation(
        self,
        contract_address: str,
        chain_id: int,
    ) -> ExplorerTransaction | None:
        """Return the contract deployment transaction when available."""

    @abstractmethod
    async def get_wallet_transactions(
        self,
        wallet_address: str,
        chain_id: int,
        *,
        limit: int = 25,
    ) -> list[ExplorerTransaction]:
        """Return normal transactions for a wallet, oldest first."""
