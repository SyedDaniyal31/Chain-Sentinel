"""M5.0 centralized EVM chain registry."""

from __future__ import annotations

from dataclasses import dataclass

from app.blockchain.dex_constants import DexAddresses
from app.core.exceptions import UnsupportedChainError

DEFAULT_CHAIN_ID = 1


@dataclass(frozen=True, slots=True)
class ChainDefinition:
    """Canonical metadata for a supported EVM chain."""

    chain_id: int
    display_name: str
    native_currency: str
    rpc_url: str
    explorer_url: str
    explorer_api_base: str
    supported: bool = True
    testnet: bool = False
    dex_addresses: DexAddresses | None = None


def _build_default_chains() -> dict[int, ChainDefinition]:
    """Return the built-in supported chain catalog."""
    return {
        1: ChainDefinition(
            chain_id=1,
            display_name="Ethereum Mainnet",
            native_currency="ETH",
            rpc_url="https://ethereum-rpc.publicnode.com",
            explorer_url="https://etherscan.io",
            explorer_api_base="https://api.etherscan.io/api",
            testnet=False,
            dex_addresses=DexAddresses(
                weth="0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",
                router="0x7a250d5630b4cf539739df2c5dacb4c659f2488d",
                factory="0x5c69bee701ef814a2b6a3edd4b1652cb9cc5aa6f",
            ),
        ),
        11155111: ChainDefinition(
            chain_id=11155111,
            display_name="Ethereum Sepolia",
            native_currency="ETH",
            rpc_url="https://ethereum-sepolia-rpc.publicnode.com",
            explorer_url="https://sepolia.etherscan.io",
            explorer_api_base="https://api-sepolia.etherscan.io/api",
            testnet=True,
            dex_addresses=DexAddresses(
                weth="0xfff9976782d46cc05630d1f9ebabe19216337aaf",
                router="0xc532a74256d3db42d0bb7b040438bed69799a8cc",
                factory="0x7e0987e5b3a30e3f2828572cd659dd524b256b59",
            ),
        ),
        8453: ChainDefinition(
            chain_id=8453,
            display_name="Base",
            native_currency="ETH",
            rpc_url="https://mainnet.base.org",
            explorer_url="https://basescan.org",
            explorer_api_base="https://api.basescan.org/api",
            testnet=False,
        ),
        42161: ChainDefinition(
            chain_id=42161,
            display_name="Arbitrum One",
            native_currency="ETH",
            rpc_url="https://arb1.arbitrum.io/rpc",
            explorer_url="https://arbiscan.io",
            explorer_api_base="https://api.arbiscan.io/api",
            testnet=False,
        ),
        137: ChainDefinition(
            chain_id=137,
            display_name="Polygon",
            native_currency="MATIC",
            rpc_url="https://polygon-rpc.com",
            explorer_url="https://polygonscan.com",
            explorer_api_base="https://api.polygonscan.com/api",
            testnet=False,
        ),
        56: ChainDefinition(
            chain_id=56,
            display_name="BNB Chain",
            native_currency="BNB",
            rpc_url="https://bsc-dataseed.binance.org",
            explorer_url="https://bscscan.com",
            explorer_api_base="https://api.bscscan.com/api",
            testnet=False,
        ),
    }


class ChainRegistry:
    """Lookup and enumerate supported EVM chains."""

    def __init__(self, chains: dict[int, ChainDefinition] | None = None) -> None:
        self._chains = chains or _build_default_chains()

    def get(self, chain_id: int) -> ChainDefinition:
        """Return a chain definition or raise UnsupportedChainError."""
        chain = self._chains.get(chain_id)
        if chain is None or not chain.supported:
            raise UnsupportedChainError(chain_id)
        return chain

    def try_get(self, chain_id: int) -> ChainDefinition | None:
        """Return a supported chain definition when available."""
        chain = self._chains.get(chain_id)
        if chain is None or not chain.supported:
            return None
        return chain

    def is_supported(self, chain_id: int) -> bool:
        return self.try_get(chain_id) is not None

    def list_supported(self) -> list[ChainDefinition]:
        return sorted(
            (chain for chain in self._chains.values() if chain.supported),
            key=lambda chain: (chain.testnet, chain.chain_id),
        )

    def get_rpc_url(self, chain_id: int, *, override_url: str | None = None) -> str:
        chain = self.get(chain_id)
        if override_url:
            return override_url
        return chain.rpc_url

    def get_explorer_api_base(self, chain_id: int) -> str | None:
        chain = self.try_get(chain_id)
        return chain.explorer_api_base if chain else None

    def get_dex_addresses(self, chain_id: int) -> DexAddresses | None:
        chain = self.try_get(chain_id)
        return chain.dex_addresses if chain else None


_default_registry: ChainRegistry | None = None


def get_chain_registry() -> ChainRegistry:
    """Return the process-wide default chain registry."""
    global _default_registry
    if _default_registry is None:
        _default_registry = ChainRegistry()
    return _default_registry
