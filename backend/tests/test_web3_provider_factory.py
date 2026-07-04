"""M5.0 Web3ProviderFactory unit tests."""

import pytest

from app.blockchain.chain_registry import ChainRegistry, ChainDefinition
from app.blockchain.web3_provider_factory import Web3ProviderFactory
from app.core.config import Settings
from app.core.exceptions import UnsupportedChainError


@pytest.fixture
def settings() -> Settings:
    return Settings(
        eth_rpc_url="https://custom-sepolia.example",
        chain_id=11155111,
        eth_rpc_timeout_seconds=5,
    )


def test_factory_returns_web3_for_supported_chain(settings: Settings) -> None:
    factory = Web3ProviderFactory(settings)
    web3 = factory.get_web3(1)
    assert web3.provider.endpoint_uri == "https://ethereum-rpc.publicnode.com"


def test_factory_applies_settings_rpc_override_for_primary_chain(settings: Settings) -> None:
    factory = Web3ProviderFactory(settings)
    web3 = factory.get_web3(11155111)
    assert web3.provider.endpoint_uri == "https://custom-sepolia.example"


def test_factory_caches_clients(settings: Settings) -> None:
    factory = Web3ProviderFactory(settings)
    assert factory.get_web3(1) is factory.get_web3(1)


def test_factory_rejects_unsupported_chain(settings: Settings) -> None:
    factory = Web3ProviderFactory(settings)
    with pytest.raises(UnsupportedChainError):
        factory.get_web3(999)


def test_get_rpc_url_uses_registry_default(settings: Settings) -> None:
    factory = Web3ProviderFactory(settings)
    assert factory.get_rpc_url(8453) == "https://mainnet.base.org"
