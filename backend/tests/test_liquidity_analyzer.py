"""LiquidityAnalyzer unit tests (M5.1)."""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.blockchain.dex.dex_provider import PoolDiscovery
from app.services.liquidity_analyzer import LiquidityAnalyzer


def _pool(dex_name: str, liquidity_native: float) -> PoolDiscovery:
    return PoolDiscovery(
        dex_name=dex_name,
        pair_address="0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
        token0="0x1111111111111111111111111111111111111111",
        token1="0x2222222222222222222222222222222222222222",
        reserve0=1,
        reserve1=1,
        liquidity_native=liquidity_native,
        lp_total_supply=1_000,
        lp_burned_balance=500,
        lp_zero_balance=0,
        lp_top_holder="0x000000000000000000000000000000000000dead",
        lp_top_holder_balance=500,
    )


class _FakeRegistry:
    def __init__(self, providers: list[MagicMock]) -> None:
        self._providers = providers

    def list_providers(self) -> list[MagicMock]:
        return self._providers


@pytest.mark.asyncio
async def test_liquidity_analyzer_aggregates_provider_discoveries() -> None:
    uniswap = MagicMock()
    uniswap.name = "uniswap"
    uniswap.discover_pool = AsyncMock(return_value=_pool("uniswap", 12.0))

    sushiswap = MagicMock()
    sushiswap.name = "sushiswap"
    sushiswap.discover_pool = AsyncMock(return_value=_pool("sushiswap", 4.0))

    web3 = MagicMock()
    analyzer = LiquidityAnalyzer(
        web3,
        chain_id=1,
        provider_registry=_FakeRegistry([uniswap, sushiswap]),
    )

    result = await analyzer.analyze("0x742d35cc6634c0532925a3b844bc9e7595f0beb0")

    assert result.has_liquidity is True
    assert result.primary_dex == "uniswap"
    assert result.liquidity_usd == Decimal("36000.00")
    assert result.liquidity_locked is True
    assert len(result.top_pools) == 2


@pytest.mark.asyncio
async def test_liquidity_analyzer_returns_empty_when_no_providers() -> None:
    web3 = MagicMock()
    analyzer = LiquidityAnalyzer(web3, chain_id=1, provider_registry=_FakeRegistry([]))

    result = await analyzer.analyze("0x742d35cc6634c0532925a3b844bc9e7595f0beb0")

    assert result.has_liquidity is False
    assert result.top_pools == []


@pytest.mark.asyncio
async def test_liquidity_analyzer_ignores_failed_provider() -> None:
    failing = MagicMock()
    failing.name = "uniswap"
    failing.discover_pool = AsyncMock(side_effect=RuntimeError("rpc down"))

    working = MagicMock()
    working.name = "baseswap"
    working.discover_pool = AsyncMock(return_value=_pool("baseswap", 2.0))

    web3 = MagicMock()
    analyzer = LiquidityAnalyzer(
        web3,
        chain_id=8453,
        provider_registry=_FakeRegistry([failing, working]),
    )

    result = await analyzer.analyze("0x742d35cc6634c0532925a3b844bc9e7595f0beb0")

    assert result.has_liquidity is True
    assert result.primary_dex == "baseswap"
