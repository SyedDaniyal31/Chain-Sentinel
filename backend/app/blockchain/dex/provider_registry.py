"""Resolve DEX providers per chain via ChainRegistry (M5.1)."""

from __future__ import annotations

from dataclasses import dataclass

from web3 import AsyncWeb3

from app.blockchain.chain_registry import ChainRegistry, get_chain_registry
from app.blockchain.dex.dex_provider import DexProvider
from app.blockchain.dex.uniswap_v2_provider import UniswapV2DexProvider
from app.core.exceptions import UnsupportedChainError


@dataclass(frozen=True, slots=True)
class DexDeployment:
    """Factory/WETH deployment for a named DEX on a chain."""

    name: str
    factory: str
    weth: str


CHAIN_DEX_DEPLOYMENTS: dict[int, list[DexDeployment]] = {
    1: [
        DexDeployment(
            name="uniswap",
            factory="0x5c69bee701ef814a2b6a3edd4b1652cb9cc5aa6f",
            weth="0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",
        ),
        DexDeployment(
            name="sushiswap",
            factory="0xc0aeae478e3658e2610c5f7a4a2e1777cE9e4f2c",
            weth="0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",
        ),
    ],
    11155111: [
        DexDeployment(
            name="uniswap",
            factory="0x7e0987e5b3a30e3f2828572cd659dd524b256b59",
            weth="0xfff9976782d46cc05630d1f9ebabe19216337aaf",
        ),
    ],
    8453: [
        DexDeployment(
            name="baseswap",
            factory="0x8909dc15e40113ff468687c6dc1bf5a6a0923bbf",
            weth="0x4200000000000000000000000000000000000006",
        ),
        DexDeployment(
            name="aerodrome",
            factory="0x420DD381b31aEf6683db6B902084cB0FFECe40Da",
            weth="0x4200000000000000000000000000000000000006",
        ),
    ],
    42161: [
        DexDeployment(
            name="sushiswap",
            factory="0xc35dadb65012ec5796536b9864ed8773abc74c4",
            weth="0x82af49447d8a07e3bd80bd8756a6618750248443",
        ),
    ],
    137: [
        DexDeployment(
            name="quickswap",
            factory="0x5757371414417be8c6a63257e4bd4549a247e0c0",
            weth="0x0d500b1d8e8ef31e21c99d1db9a6444adf4350a0",
        ),
    ],
    56: [
        DexDeployment(
            name="pancakeswap",
            factory="0xcA143Ce32Fe78f1f7019d7d551a6402fC5350c73",
            weth="0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c",
        ),
    ],
}


class DexProviderRegistry:
    """Build chain-scoped DEX provider instances."""

    def __init__(
        self,
        web3: AsyncWeb3,
        chain_id: int,
        registry: ChainRegistry | None = None,
    ) -> None:
        self._web3 = web3
        self._chain_id = chain_id
        self._registry = registry or get_chain_registry()

    def list_providers(self) -> list[DexProvider]:
        if not self._registry.is_supported(self._chain_id):
            raise UnsupportedChainError(self._chain_id)

        deployments = CHAIN_DEX_DEPLOYMENTS.get(self._chain_id, [])
        if not deployments:
            chain = self._registry.get(self._chain_id)
            if chain.dex_addresses is None:
                return []
            deployments = [
                DexDeployment(
                    name="uniswap",
                    factory=chain.dex_addresses.factory,
                    weth=chain.dex_addresses.weth,
                )
            ]

        return [
            UniswapV2DexProvider(
                self._web3,
                name=deployment.name,
                factory_address=deployment.factory,
                weth_address=deployment.weth,
            )
            for deployment in deployments
        ]


def get_dex_provider_registry(web3: AsyncWeb3, chain_id: int) -> DexProviderRegistry:
    return DexProviderRegistry(web3, chain_id)
