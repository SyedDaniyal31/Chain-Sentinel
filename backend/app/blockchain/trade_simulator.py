"""Fork-based buy / transfer / sell simulation on Anvil."""

from __future__ import annotations

import logging
import time

from app.blockchain.anvil_client import AnvilForkConfig, AnvilRpcClient
from app.blockchain.dex_constants import DexAddresses, get_dex_addresses
from app.blockchain.honeypot_simulation import HoneypotSimulationResult
from app.blockchain.honeypot_simulation_state import HoneypotSimulationState, HoneypotTradePathResult
from app.blockchain.trade_encoding import (
    DEFAULT_SIMULATION_DEADLINE_OFFSET,
    MAX_UINT256,
    compute_tax_bps,
    decode_address,
    decode_amounts_out,
    decode_uint256,
    encode_approve,
    encode_balance_of,
    encode_get_amounts_out,
    encode_get_pair,
    encode_swap_eth_for_tokens,
    encode_swap_tokens_for_eth,
    encode_transfer,
)
from app.core.validators import normalize_eth_address
from app.models.enums import HoneypotSimulationStatus

logger = logging.getLogger(__name__)

# Foundry Anvil default funded accounts.
SIM_BUYER = "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266"
SIM_RECIPIENT = "0x70997970C51812dc3A010C7d01b50e0d17dc79C8"


class TradeSimulator:
    """
    Execute a round-trip DEX trade on an Anvil mainnet fork.

    Steps:
        1. Locate Uniswap V2 pair for token/WETH
        2. Buy token with ETH (measures buy tax)
        3. Transfer token to second wallet (transfer restriction probe)
        4. Sell token back to ETH (measures sell tax / honeypot confirmation)
    """

    def __init__(
        self,
        anvil_client: AnvilRpcClient,
        *,
        eth_amount_wei: int = 10**17,
    ) -> None:
        self._anvil = anvil_client
        self._eth_amount_wei = eth_amount_wei

    async def simulate(
        self,
        token_address: str,
        chain_id: int,
        *,
        fork_config: AnvilForkConfig,
    ) -> HoneypotSimulationResult:
        token = normalize_eth_address(token_address)
        dex = get_dex_addresses(chain_id)
        if dex is None:
            logger.info("Trade simulation unsupported for chain_id=%s", chain_id)
            return HoneypotSimulationResult(simulated=False)

        buy = HoneypotTradePathResult()
        transfer = HoneypotTradePathResult()
        sell = HoneypotTradePathResult()

        try:
            await self._anvil.reset_fork(fork_config)
            await self._anvil.set_balance(SIM_BUYER, 5 * 10**18)
            await self._anvil.set_balance(SIM_RECIPIENT, 0)

            pair_address = await self._find_pair(token, dex)
            if pair_address is None:
                return self._result(
                    dex=dex,
                    pair_address=None,
                    fork_block=fork_config.block_number,
                    status=HoneypotSimulationStatus.SKIPPED,
                    buy=buy,
                    transfer=transfer,
                    sell=sell,
                    can_buy=False,
                    can_sell=False,
                    can_transfer=None,
                )

            buy_path = [dex.weth, token]
            sell_path = [token, dex.weth]
            deadline = int(time.time()) + DEFAULT_SIMULATION_DEADLINE_OFFSET

            buy_quote = await self._quote_amounts_out(dex.router, self._eth_amount_wei, buy_path)
            buy.attempted = True
            if not buy_quote:
                buy.success = False
                buy.revert_reason = "NO_BUY_QUOTE"
                return self._result(
                    dex=dex,
                    pair_address=pair_address,
                    fork_block=fork_config.block_number,
                    buy=buy,
                    transfer=transfer,
                    sell=sell,
                    can_buy=False,
                    can_sell=False,
                    can_transfer=None,
                )

            expected_tokens = buy_quote[-1]
            buy_ok = await self._execute_buy(
                token=token,
                dex=dex,
                path=buy_path,
                deadline=deadline,
                buyer=SIM_BUYER,
            )
            buy.success = buy_ok
            if not buy_ok:
                buy.revert_reason = "SWAP_ETH_FOR_TOKENS_FAILED"
                return self._result(
                    dex=dex,
                    pair_address=pair_address,
                    fork_block=fork_config.block_number,
                    buy=buy,
                    transfer=transfer,
                    sell=sell,
                    can_buy=False,
                    can_sell=False,
                    can_transfer=None,
                )

            actual_tokens = await self._token_balance(token, SIM_BUYER)
            buy.tax_bps = compute_tax_bps(expected_tokens, actual_tokens)

            transfer_amount = actual_tokens // 4 if actual_tokens > 0 else 0
            transfer_ok = True
            if transfer_amount > 0:
                transfer.attempted = True
                transfer_ok = await self._execute_transfer(
                    token=token,
                    sender=SIM_BUYER,
                    recipient=SIM_RECIPIENT,
                    amount=transfer_amount,
                )
                transfer.success = transfer_ok
                if not transfer_ok:
                    transfer.revert_reason = "TRANSFER_FAILED"

            sellable_balance = await self._token_balance(token, SIM_BUYER)
            if sellable_balance == 0 or not transfer_ok:
                return self._result(
                    dex=dex,
                    pair_address=pair_address,
                    fork_block=fork_config.block_number,
                    buy=buy,
                    transfer=transfer,
                    sell=sell,
                    can_buy=True,
                    can_sell=False,
                    can_transfer=transfer_ok if transfer.attempted else None,
                    buy_tax_bps=buy.tax_bps,
                )

            sell_quote = await self._quote_amounts_out(dex.router, sellable_balance, sell_path)
            expected_eth = sell_quote[-1] if sell_quote else 0
            eth_before = await self._anvil.get_balance(SIM_BUYER)

            sell.attempted = True
            sell_ok = await self._execute_sell(
                token=token,
                dex=dex,
                path=sell_path,
                deadline=deadline,
                seller=SIM_BUYER,
                amount_in=sellable_balance,
            )
            sell.success = sell_ok
            if not sell_ok:
                sell.revert_reason = "SWAP_TOKENS_FOR_ETH_FAILED"

            eth_after = await self._anvil.get_balance(SIM_BUYER)
            actual_eth = max(eth_after - eth_before, 0)
            sell.tax_bps = compute_tax_bps(expected_eth, actual_eth)

            return self._result(
                dex=dex,
                pair_address=pair_address,
                fork_block=fork_config.block_number,
                buy=buy,
                transfer=transfer,
                sell=sell,
                can_buy=True,
                can_sell=sell_ok,
                can_transfer=transfer_ok if transfer.attempted else None,
                buy_tax_bps=buy.tax_bps,
                sell_tax_bps=sell.tax_bps,
            )
        except Exception:
            logger.exception("Trade simulation failed for token %s", token)
            return HoneypotSimulationResult(
                simulated=False,
                simulation=HoneypotSimulationState(status=HoneypotSimulationStatus.FAILED),
            )

    def _result(
        self,
        *,
        dex: DexAddresses,
        pair_address: str | None,
        fork_block: int | None,
        buy: HoneypotTradePathResult,
        transfer: HoneypotTradePathResult,
        sell: HoneypotTradePathResult,
        can_buy: bool,
        can_sell: bool,
        can_transfer: bool | None,
        buy_tax_bps: int | None = None,
        sell_tax_bps: int | None = None,
        status: HoneypotSimulationStatus = HoneypotSimulationStatus.COMPLETED,
    ) -> HoneypotSimulationResult:
        round_trip_success = (
            buy.success is True
            and (not transfer.attempted or transfer.success is True)
            and (not sell.attempted or sell.success is True)
        )
        simulation = HoneypotSimulationState(
            status=status,
            fork_block=fork_block,
            pair_address=pair_address,
            router_address=dex.router,
            buy=buy,
            transfer=transfer,
            sell=sell,
            round_trip_success=round_trip_success,
        )
        return HoneypotSimulationResult(
            can_buy=can_buy,
            can_sell=can_sell,
            can_transfer=can_transfer,
            buy_tax_bps=buy_tax_bps if buy_tax_bps is not None else buy.tax_bps,
            sell_tax_bps=sell_tax_bps if sell_tax_bps is not None else sell.tax_bps,
            simulated=True,
            simulation=simulation,
        )

    async def _find_pair(self, token: str, dex: DexAddresses) -> str | None:
        data = encode_get_pair(token, dex.weth)
        result = await self._anvil.eth_call({"to": dex.factory, "data": data})
        return decode_address(result)

    async def _quote_amounts_out(
        self,
        router: str,
        amount_in: int,
        path: list[str],
    ) -> list[int]:
        data = encode_get_amounts_out(amount_in, path)
        result = await self._anvil.eth_call({"to": router, "data": data})
        return decode_amounts_out(result)

    async def _token_balance(self, token: str, holder: str) -> int:
        data = encode_balance_of(holder)
        result = await self._anvil.eth_call({"to": token, "data": data})
        return decode_uint256(result)

    async def _execute_buy(
        self,
        *,
        token: str,
        dex: DexAddresses,
        path: list[str],
        deadline: int,
        buyer: str,
    ) -> bool:
        data = encode_swap_eth_for_tokens(0, path, buyer, deadline)
        await self._anvil.impersonate_account(buyer)
        try:
            tx_hash = await self._anvil.eth_send_transaction(
                {
                    "from": buyer,
                    "to": dex.router,
                    "data": data,
                    "value": hex(self._eth_amount_wei),
                }
            )
            return await self._anvil.wait_for_transaction(tx_hash)
        finally:
            await self._anvil.stop_impersonating_account(buyer)

    async def _execute_transfer(
        self,
        *,
        token: str,
        sender: str,
        recipient: str,
        amount: int,
    ) -> bool:
        data = encode_transfer(recipient, amount)
        await self._anvil.impersonate_account(sender)
        try:
            tx_hash = await self._anvil.eth_send_transaction(
                {
                    "from": sender,
                    "to": token,
                    "data": data,
                }
            )
            return await self._anvil.wait_for_transaction(tx_hash)
        finally:
            await self._anvil.stop_impersonating_account(sender)

    async def _execute_sell(
        self,
        *,
        token: str,
        dex: DexAddresses,
        path: list[str],
        deadline: int,
        seller: str,
        amount_in: int,
    ) -> bool:
        approve_data = encode_approve(dex.router, MAX_UINT256)
        await self._anvil.impersonate_account(seller)
        try:
            approve_hash = await self._anvil.eth_send_transaction(
                {
                    "from": seller,
                    "to": token,
                    "data": approve_data,
                }
            )
            if not await self._anvil.wait_for_transaction(approve_hash):
                return False

            sell_data = encode_swap_tokens_for_eth(amount_in, 0, path, seller, deadline)
            sell_hash = await self._anvil.eth_send_transaction(
                {
                    "from": seller,
                    "to": dex.router,
                    "data": sell_data,
                }
            )
            return await self._anvil.wait_for_transaction(sell_hash)
        finally:
            await self._anvil.stop_impersonating_account(seller)
