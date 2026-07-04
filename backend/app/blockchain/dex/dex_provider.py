"""DEX provider abstraction for liquidity discovery."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PoolDiscovery:
    """On-chain liquidity pool snapshot from a single DEX provider."""

    dex_name: str
    pair_address: str
    token0: str
    token1: str
    reserve0: int
    reserve1: int
    liquidity_native: float
    lp_total_supply: int
    lp_burned_balance: int
    lp_zero_balance: int
    lp_top_holder: str | None
    lp_top_holder_balance: int


class DexProvider(ABC):
    """Discover Uniswap-style V2 pools for a token on a specific chain."""

    name: str

    @abstractmethod
    async def discover_pool(self, token_address: str) -> PoolDiscovery | None:
        """Return pool metadata when a WETH/native pair exists with liquidity."""
