"""Liquidity intelligence builders for M5.1."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from app.blockchain.dex.dex_provider import PoolDiscovery
from app.schemas.scan_result import LiquidityAnalysisData, LiquidityIntelligenceData, LiquidityPoolData

DEAD_ADDRESS = "0x000000000000000000000000000000000000dead"
ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"
LOW_LIQUIDITY_NATIVE = 1.0
NATIVE_USD_ESTIMATE = Decimal("3000")


def estimate_liquidity_usd(liquidity_native: float) -> Decimal:
    """Approximate USD depth using a static native currency reference price."""
    return (Decimal(str(liquidity_native)) * NATIVE_USD_ESTIMATE).quantize(Decimal("0.01"))


def analyze_lp_lock(pool: PoolDiscovery) -> tuple[bool, Decimal, datetime | None]:
    """Detect burned/locked LP based on dead and zero address balances."""
    if pool.lp_total_supply <= 0:
        return False, Decimal("0.00"), None

    locked_amount = pool.lp_burned_balance + pool.lp_zero_balance
    percentage = (Decimal(locked_amount) / Decimal(pool.lp_total_supply) * Decimal("100")).quantize(
        Decimal("0.01")
    )
    is_locked = percentage >= Decimal("50.00")
    return is_locked, percentage, None


def pool_to_data(pool: PoolDiscovery) -> LiquidityPoolData:
    locked, lock_pct, lock_expiry = analyze_lp_lock(pool)
    return LiquidityPoolData(
        dex=pool.dex_name,
        pair_address=pool.pair_address,
        token0=pool.token0,
        token1=pool.token1,
        reserve0=str(pool.reserve0),
        reserve1=str(pool.reserve1),
        liquidity_native=round(pool.liquidity_native, 6),
        liquidity_usd=estimate_liquidity_usd(pool.liquidity_native),
        lp_total_supply=str(pool.lp_total_supply),
        lp_owner=pool.lp_top_holder,
        lp_owner_balance=str(pool.lp_top_holder_balance),
        liquidity_locked=locked,
        liquidity_lock_percentage=lock_pct,
        lock_expiry=lock_expiry,
    )


def build_liquidity_analysis(pools: list[PoolDiscovery]) -> LiquidityAnalysisData:
    """Aggregate pool discoveries into primary liquidity intelligence."""
    if not pools:
        return LiquidityAnalysisData(
            has_liquidity=False,
            liquidity_usd=Decimal("0.00"),
            primary_dex=None,
            pair_address=None,
            lp_owner=None,
            liquidity_locked=False,
            liquidity_lock_percentage=Decimal("0.00"),
            lock_expiry=None,
            top_pools=[],
        )

    sorted_pools = sorted(pools, key=lambda pool: pool.liquidity_native, reverse=True)
    primary = sorted_pools[0]
    top_pool_data = [pool_to_data(pool) for pool in sorted_pools[:5]]
    primary_data = top_pool_data[0]
    locked, lock_pct, lock_expiry = analyze_lp_lock(primary)

    return LiquidityAnalysisData(
        has_liquidity=True,
        liquidity_usd=primary_data.liquidity_usd,
        primary_dex=primary.dex_name,
        pair_address=primary.pair_address,
        lp_owner=primary.lp_top_holder,
        liquidity_locked=locked,
        liquidity_lock_percentage=lock_pct,
        lock_expiry=lock_expiry,
        top_pools=top_pool_data,
    )


def to_intelligence(analysis: LiquidityAnalysisData) -> LiquidityIntelligenceData:
    return LiquidityIntelligenceData(
        has_liquidity=analysis.has_liquidity,
        liquidity_usd=analysis.liquidity_usd,
        primary_dex=analysis.primary_dex,
        pair_address=analysis.pair_address,
        lp_owner=analysis.lp_owner,
        liquidity_locked=analysis.liquidity_locked,
        liquidity_lock_percentage=analysis.liquidity_lock_percentage,
        lock_expiry=analysis.lock_expiry,
        top_pools=analysis.top_pools,
    )


def empty_liquidity_analysis() -> LiquidityAnalysisData:
    return build_liquidity_analysis([])
