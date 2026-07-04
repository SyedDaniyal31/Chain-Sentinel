"""Architecture for fork-based honeypot trade simulation."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.blockchain.honeypot import HoneypotFlags
from app.blockchain.honeypot_simulation_state import HoneypotSimulationState
from app.core.config import Settings


@dataclass(frozen=True, slots=True)
class HoneypotSimulationResult:
    """
    Outcome of a simulated buy/transfer/sell path on an Anvil fork.

    When ``simulated`` is False the provider deferred to heuristic analysis.
    """

    can_buy: bool | None = None
    can_sell: bool | None = None
    can_transfer: bool | None = None
    buy_tax_bps: int | None = None
    sell_tax_bps: int | None = None
    simulated: bool = False
    simulation: HoneypotSimulationState | None = None

    @property
    def trade_simulated(self) -> bool:
        return self.simulated

    def to_honeypot_flags(self) -> HoneypotFlags:
        """Map confirmed simulation outcomes into honeypot indicator booleans."""
        flags = HoneypotFlags()
        if not self.simulated:
            return flags

        if self.can_sell is False:
            return HoneypotFlags(blacklist_sell_blocking=True)

        if self.sell_tax_bps is not None and self.sell_tax_bps >= 5000:
            return HoneypotFlags(transfer_tax_control=True)

        if self.buy_tax_bps is not None and self.buy_tax_bps >= 5000:
            return HoneypotFlags(transfer_tax_control=True)

        return flags


class HoneypotSimulationProvider(ABC):
    """
    Pluggable trade simulation for Rug Pull Detector V3+ / M4.1.

    Implementations fork mainnet state via Anvil and attempt a round-trip
    buy → transfer → sell to confirm honeypot behavior and measure taxes.
    """

    @abstractmethod
    async def simulate_trade_paths(
        self,
        token_address: str,
        chain_id: int,
        *,
        pair_address: str | None = None,
    ) -> HoneypotSimulationResult | None:
        """Execute buy → transfer → sell on an Anvil fork."""

    async def simulate_trade(
        self,
        token_address: str,
        chain_id: int,
        *,
        pair_address: str | None = None,
    ) -> HoneypotSimulationResult | None:
        """Backward-compatible alias for ``simulate_trade_paths``."""
        return await self.simulate_trade_paths(
            token_address,
            chain_id,
            pair_address=pair_address,
        )


class NullHoneypotSimulationProvider(HoneypotSimulationProvider):
    """Default no-op provider — heuristic detection only when simulation is disabled."""

    async def simulate_trade_paths(
        self,
        token_address: str,
        chain_id: int,
        *,
        pair_address: str | None = None,
    ) -> HoneypotSimulationResult | None:
        return None


def create_honeypot_simulation_provider(settings: Settings) -> HoneypotSimulationProvider:
    """Build the configured honeypot simulation backend."""
    if not settings.trade_simulation_enabled:
        return NullHoneypotSimulationProvider()

    from app.blockchain.anvil_honeypot_simulation import AnvilHoneypotSimulationProvider
    from app.blockchain.chain_registry import DEFAULT_CHAIN_ID, get_chain_registry
    from app.blockchain.web3_provider_factory import create_web3_provider_factory

    chain_id = settings.chain_id or DEFAULT_CHAIN_ID
    factory = create_web3_provider_factory(settings)
    fork_rpc_url = settings.fork_rpc_url or factory.get_rpc_url(chain_id)
    return AnvilHoneypotSimulationProvider(
        anvil_rpc_url=settings.anvil_rpc_url,
        fork_rpc_url=fork_rpc_url,
        chain_id=chain_id,
        eth_amount_wei=settings.simulation_eth_amount_wei,
        fork_block_number=settings.simulation_fork_block_number,
        auto_start_anvil=settings.anvil_auto_start,
        anvil_binary=settings.anvil_binary,
        timeout_seconds=settings.eth_rpc_timeout_seconds,
    )
