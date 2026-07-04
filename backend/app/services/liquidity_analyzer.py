"""M5.1 liquidity pool discovery and LP ownership analysis."""

from __future__ import annotations

import logging

from web3 import AsyncWeb3

from app.blockchain.dex.provider_registry import DexProviderRegistry, get_dex_provider_registry
from app.blockchain.liquidity_intelligence import build_liquidity_analysis, empty_liquidity_analysis
from app.core.validators import normalize_eth_address
from app.schemas.scan_result import LiquidityAnalysisData

logger = logging.getLogger(__name__)


class LiquidityAnalyzer:
    """Discover DEX liquidity and LP lock status for ERC20-style tokens."""

    def __init__(
        self,
        web3: AsyncWeb3,
        chain_id: int,
        provider_registry: DexProviderRegistry | None = None,
    ) -> None:
        self._web3 = web3
        self._chain_id = chain_id
        self._provider_registry = provider_registry or get_dex_provider_registry(web3, chain_id)

    async def analyze(self, token_address: str) -> LiquidityAnalysisData:
        """Discover pools across configured DEX providers for the target token."""
        normalized = normalize_eth_address(token_address)
        providers = self._provider_registry.list_providers()
        if not providers:
            logger.info("No DEX providers configured for chain_id=%s", self._chain_id)
            return empty_liquidity_analysis()

        discoveries = []
        for provider in providers:
            try:
                pool = await provider.discover_pool(normalized)
            except Exception:
                logger.debug(
                    "Pool discovery failed for %s on %s",
                    normalized,
                    provider.name,
                    exc_info=True,
                )
                continue
            if pool is not None:
                discoveries.append(pool)

        return build_liquidity_analysis(discoveries)
