"""M5.0 ChainRegistry unit tests."""

import pytest

from app.blockchain.chain_registry import ChainRegistry, DEFAULT_CHAIN_ID, get_chain_registry
from app.core.exceptions import UnsupportedChainError


def test_default_chain_id_is_mainnet() -> None:
    assert DEFAULT_CHAIN_ID == 1


def test_registry_lists_six_supported_chains() -> None:
    registry = get_chain_registry()
    chains = registry.list_supported()
    assert len(chains) == 6
    chain_ids = {chain.chain_id for chain in chains}
    assert chain_ids == {1, 11155111, 8453, 42161, 137, 56}


def test_registry_get_mainnet_metadata() -> None:
    chain = get_chain_registry().get(1)
    assert chain.display_name == "Ethereum Mainnet"
    assert chain.native_currency == "ETH"
    assert chain.explorer_api_base == "https://api.etherscan.io/api"
    assert chain.testnet is False


def test_registry_marks_sepolia_as_testnet() -> None:
    chain = get_chain_registry().get(11155111)
    assert chain.testnet is True
    assert "sepolia" in chain.explorer_api_base


def test_registry_base_explorer_api() -> None:
    chain = get_chain_registry().get(8453)
    assert chain.explorer_api_base == "https://api.basescan.org/api"


def test_registry_unsupported_chain_raises() -> None:
    with pytest.raises(UnsupportedChainError):
        get_chain_registry().get(999)


def test_registry_dex_addresses_only_on_simulation_chains() -> None:
    registry = get_chain_registry()
    assert registry.get_dex_addresses(1) is not None
    assert registry.get_dex_addresses(11155111) is not None
    assert registry.get_dex_addresses(8453) is None


def test_custom_registry_override() -> None:
    from app.blockchain.chain_registry import ChainDefinition

    registry = ChainRegistry(
        {
            999: ChainDefinition(
                chain_id=999,
                display_name="Custom",
                native_currency="ETH",
                rpc_url="https://rpc.example",
                explorer_url="https://explorer.example",
                explorer_api_base="https://api.explorer.example/api",
            )
        }
    )
    assert registry.is_supported(999)
    assert registry.get_explorer_api_base(999) == "https://api.explorer.example/api"
