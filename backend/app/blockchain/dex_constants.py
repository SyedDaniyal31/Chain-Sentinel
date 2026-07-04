"""Uniswap V2 and WETH addresses per chain for trade simulation."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DexAddresses:
    """DEX contracts required for fork-based swap simulation."""

    weth: str
    router: str
    factory: str


def get_dex_addresses(chain_id: int) -> DexAddresses | None:
    """Return known DEX deployment for a chain via ChainRegistry."""
    from app.blockchain.chain_registry import get_chain_registry

    return get_chain_registry().get_dex_addresses(chain_id)
