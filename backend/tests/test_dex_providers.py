"""DEX provider registry unit tests (M5.1)."""

from unittest.mock import MagicMock

import pytest

from app.blockchain.dex.provider_registry import DexProviderRegistry, get_dex_provider_registry
from app.core.exceptions import UnsupportedChainError


def test_registry_lists_uniswap_and_sushiswap_on_mainnet() -> None:
    web3 = MagicMock()
    registry = DexProviderRegistry(web3, chain_id=1)

    providers = registry.list_providers()

    assert [provider.name for provider in providers] == ["uniswap", "sushiswap"]


def test_registry_lists_pancakeswap_on_bsc() -> None:
    web3 = MagicMock()
    registry = DexProviderRegistry(web3, chain_id=56)

    providers = registry.list_providers()

    assert [provider.name for provider in providers] == ["pancakeswap"]


def test_registry_lists_baseswap_and_aerodrome_on_base() -> None:
    web3 = MagicMock()
    registry = DexProviderRegistry(web3, chain_id=8453)

    providers = registry.list_providers()

    assert [provider.name for provider in providers] == ["baseswap", "aerodrome"]


def test_get_dex_provider_registry_factory() -> None:
    web3 = MagicMock()
    registry = get_dex_provider_registry(web3, 11155111)

    providers = registry.list_providers()

    assert len(providers) == 1
    assert providers[0].name == "uniswap"


def test_registry_rejects_unsupported_chain() -> None:
    web3 = MagicMock()
    registry = DexProviderRegistry(web3, chain_id=99999)

    with pytest.raises(UnsupportedChainError):
        registry.list_providers()
