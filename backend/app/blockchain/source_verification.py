"""Verified contract source retrieval — backward-compatible facade (M4.2 / M5.0)."""

from __future__ import annotations

from app.blockchain.chain_registry import get_chain_registry
from app.blockchain.contract_source_provider import (
    ContractMetadata,
    ContractSourceProvider,
    NullContractSourceProvider,
    VerifiedContractSource,
)
from app.blockchain.etherscan_source_provider import (
    EtherscanContractSourceProvider,
    EtherscanSourceProvider,
    ExplorerSourceProvider,
)
from app.core.config import Settings


def create_contract_source_provider(settings: Settings) -> ContractSourceProvider:
    """Build the best available explorer source provider from application settings."""
    if settings.etherscan_api_key:
        return ExplorerSourceProvider(
            settings.etherscan_api_key,
            registry=get_chain_registry(),
            timeout_seconds=settings.eth_rpc_timeout_seconds,
        )
    return NullContractSourceProvider()


def get_explorer_api_bases() -> dict[int, str]:
    """Return explorer API base URLs for all supported chains (compat helper)."""
    registry = get_chain_registry()
    return {
        chain.chain_id: chain.explorer_api_base
        for chain in registry.list_supported()
    }


__all__ = [
    "ContractMetadata",
    "ContractSourceProvider",
    "EtherscanContractSourceProvider",
    "EtherscanSourceProvider",
    "ExplorerSourceProvider",
    "NullContractSourceProvider",
    "VerifiedContractSource",
    "create_contract_source_provider",
    "get_explorer_api_bases",
]
