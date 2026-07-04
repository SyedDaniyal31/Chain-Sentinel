"""Liquidity intelligence builder unit tests (M5.1)."""

from decimal import Decimal

from app.blockchain.dex.dex_provider import PoolDiscovery
from app.blockchain.liquidity_intelligence import (
    analyze_lp_lock,
    build_liquidity_analysis,
    empty_liquidity_analysis,
    estimate_liquidity_usd,
    pool_to_data,
)


def _sample_pool(
    *,
    dex_name: str = "uniswap",
    liquidity_native: float = 10.0,
    lp_total_supply: int = 1_000_000,
    lp_burned_balance: int = 0,
    lp_zero_balance: int = 0,
    lp_top_holder: str | None = "0x1111111111111111111111111111111111111111",
    lp_top_holder_balance: int = 900_000,
) -> PoolDiscovery:
    return PoolDiscovery(
        dex_name=dex_name,
        pair_address="0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        token0="0x1111111111111111111111111111111111111111",
        token1="0x2222222222222222222222222222222222222222",
        reserve0=5_000_000_000_000_000_000,
        reserve1=5_000_000_000_000_000_000,
        liquidity_native=liquidity_native,
        lp_total_supply=lp_total_supply,
        lp_burned_balance=lp_burned_balance,
        lp_zero_balance=lp_zero_balance,
        lp_top_holder=lp_top_holder,
        lp_top_holder_balance=lp_top_holder_balance,
    )


def test_estimate_liquidity_usd_uses_static_native_price() -> None:
    assert estimate_liquidity_usd(2.0) == Decimal("6000.00")


def test_analyze_lp_lock_detects_burned_supply() -> None:
    pool = _sample_pool(lp_burned_balance=600_000, lp_top_holder_balance=400_000)

    locked, percentage, expiry = analyze_lp_lock(pool)

    assert locked is True
    assert percentage == Decimal("60.00")
    assert expiry is None


def test_analyze_lp_lock_false_when_below_threshold() -> None:
    pool = _sample_pool(lp_burned_balance=100_000, lp_top_holder_balance=900_000)

    locked, percentage, _ = analyze_lp_lock(pool)

    assert locked is False
    assert percentage == Decimal("10.00")


def test_build_liquidity_analysis_empty() -> None:
    analysis = empty_liquidity_analysis()

    assert analysis.has_liquidity is False
    assert analysis.liquidity_usd == Decimal("0.00")
    assert analysis.top_pools == []


def test_build_liquidity_analysis_selects_deepest_pool() -> None:
    shallow = _sample_pool(dex_name="sushiswap", liquidity_native=1.0)
    deep = _sample_pool(dex_name="uniswap", liquidity_native=25.0)

    analysis = build_liquidity_analysis([shallow, deep])

    assert analysis.has_liquidity is True
    assert analysis.primary_dex == "uniswap"
    assert analysis.liquidity_usd == Decimal("75000.00")
    assert len(analysis.top_pools) == 2
    assert analysis.top_pools[0].dex == "uniswap"


def test_pool_to_data_serializes_reserves() -> None:
    data = pool_to_data(_sample_pool())

    assert data.dex == "uniswap"
    assert data.reserve0 == str(5_000_000_000_000_000_000)
    assert data.lp_owner == "0x1111111111111111111111111111111111111111"
    assert data.liquidity_locked is False
