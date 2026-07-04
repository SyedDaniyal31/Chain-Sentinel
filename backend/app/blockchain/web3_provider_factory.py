"""AsyncWeb3 client factory keyed by chain_id (M5.0)."""

from __future__ import annotations

from web3 import AsyncWeb3
from web3.providers import AsyncHTTPProvider

from app.blockchain.chain_registry import ChainRegistry, get_chain_registry
from app.core.config import Settings


class Web3ProviderFactory:
    """Build and cache AsyncWeb3 clients for supported chains."""

    def __init__(
        self,
        settings: Settings,
        registry: ChainRegistry | None = None,
    ) -> None:
        self._settings = settings
        self._registry = registry or get_chain_registry()
        self._clients: dict[int, AsyncWeb3] = {}

    def get_rpc_url(self, chain_id: int) -> str:
        """Resolve the JSON-RPC URL for a supported chain."""
        chain = self._registry.get(chain_id)
        return self._resolve_rpc_url(chain)

    def get_web3(self, chain_id: int) -> AsyncWeb3:
        """Return a cached AsyncWeb3 client for the requested chain."""
        chain = self._registry.get(chain_id)
        if chain_id not in self._clients:
            rpc_url = self._resolve_rpc_url(chain)
            provider = AsyncHTTPProvider(
                rpc_url,
                request_kwargs={"timeout": self._settings.eth_rpc_timeout_seconds},
            )
            self._clients[chain_id] = AsyncWeb3(provider)
        return self._clients[chain_id]

    def _resolve_rpc_url(self, chain) -> str:
        """Apply settings override when scanning the configured primary chain."""
        if self._settings.chain_id == chain.chain_id and self._settings.eth_rpc_url:
            return self._settings.eth_rpc_url
        return chain.rpc_url


def create_web3_provider_factory(settings: Settings) -> Web3ProviderFactory:
    """Build a Web3ProviderFactory from application settings."""
    return Web3ProviderFactory(settings)
