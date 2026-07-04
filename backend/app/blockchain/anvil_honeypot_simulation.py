"""Anvil fork-based honeypot simulation provider."""

from __future__ import annotations

import logging

from app.blockchain.anvil_client import AnvilForkConfig, AnvilProcessManager, AnvilRpcClient
from app.blockchain.honeypot_simulation import HoneypotSimulationProvider, HoneypotSimulationResult
from app.blockchain.trade_simulator import TradeSimulator
from app.core.validators import normalize_eth_address

logger = logging.getLogger(__name__)


class AnvilHoneypotSimulationProvider(HoneypotSimulationProvider):
    """
    Rug Pull Detector V3 — executes real buy/transfer/sell on an Anvil fork.

    Requires either:
        - A running Anvil node at ``anvil_rpc_url`` (reset per simulation), or
        - ``auto_start_anvil=True`` to spawn a local fork process.
    """

    def __init__(
        self,
        *,
        anvil_rpc_url: str,
        fork_rpc_url: str,
        chain_id: int,
        eth_amount_wei: int = 10**17,
        fork_block_number: int | None = None,
        auto_start_anvil: bool = False,
        anvil_binary: str = "anvil",
        timeout_seconds: int = 60,
    ) -> None:
        self._configured_rpc_url = anvil_rpc_url.rstrip("/")
        self._fork_rpc_url = fork_rpc_url
        self._chain_id = chain_id
        self._eth_amount_wei = eth_amount_wei
        self._fork_block_number = fork_block_number
        self._auto_start_anvil = auto_start_anvil
        self._anvil_binary = anvil_binary
        self._timeout_seconds = timeout_seconds
        self._process_manager = AnvilProcessManager(anvil_binary=anvil_binary)

    async def simulate_trade_paths(
        self,
        token_address: str,
        chain_id: int,
        *,
        pair_address: str | None = None,
    ) -> HoneypotSimulationResult | None:
        if chain_id != self._chain_id:
            logger.debug(
                "Simulation chain mismatch (expected=%s got=%s)",
                self._chain_id,
                chain_id,
            )
            return None

        rpc_url = await self._resolve_rpc_url()
        if rpc_url is None:
            return None

        fork_config = AnvilForkConfig(
            fork_rpc_url=self._fork_rpc_url,
            chain_id=chain_id,
            block_number=self._fork_block_number,
        )
        client = AnvilRpcClient(rpc_url, timeout_seconds=self._timeout_seconds)
        simulator = TradeSimulator(client, eth_amount_wei=self._eth_amount_wei)

        result = await simulator.simulate(
            normalize_eth_address(token_address),
            chain_id,
            fork_config=fork_config,
        )
        if not result.simulated:
            return None
        return result

    async def simulate_trade(
        self,
        token_address: str,
        chain_id: int,
        *,
        pair_address: str | None = None,
    ) -> HoneypotSimulationResult | None:
        return await self.simulate_trade_paths(
            token_address,
            chain_id,
            pair_address=pair_address,
        )

    async def _resolve_rpc_url(self) -> str | None:
        if not self._auto_start_anvil:
            return self._configured_rpc_url

        try:
            return await self._process_manager.start_fork(
                AnvilForkConfig(
                    fork_rpc_url=self._fork_rpc_url,
                    chain_id=self._chain_id,
                    block_number=self._fork_block_number,
                )
            )
        except FileNotFoundError:
            logger.warning("Anvil binary unavailable — trade simulation skipped")
            return None

    async def shutdown(self) -> None:
        await self._process_manager.stop()
