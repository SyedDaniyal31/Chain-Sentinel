"""Blockchain RPC client configuration."""

from web3 import AsyncWeb3

from app.blockchain.chain_registry import DEFAULT_CHAIN_ID, get_chain_registry
from app.blockchain.web3_provider_factory import Web3ProviderFactory, create_web3_provider_factory
from app.core.config import Settings


def create_async_web3(
    settings: Settings,
    chain_id: int | None = None,
) -> AsyncWeb3:
    """Build an AsyncWeb3 client for the requested chain (backward-compatible helper)."""
    resolved_chain_id = chain_id or settings.chain_id or DEFAULT_CHAIN_ID
    factory = create_web3_provider_factory(settings)
    return factory.get_web3(resolved_chain_id)
