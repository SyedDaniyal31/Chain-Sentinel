"""Uniswap V2-compatible DEX provider implementation."""

from __future__ import annotations

import logging

from eth_abi import encode
from web3 import AsyncWeb3, Web3

from app.blockchain.dex.dex_provider import DexProvider, PoolDiscovery

logger = logging.getLogger(__name__)

ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"
DEAD_ADDRESS = "0x000000000000000000000000000000000000dead"

GET_PAIR_SELECTOR = Web3.keccak(text="getPair(address,address)")[:4].hex()
GET_RESERVES_SELECTOR = Web3.keccak(text="getReserves()")[:4].hex()
TOTAL_SUPPLY_SELECTOR = Web3.keccak(text="totalSupply()")[:4].hex()
BALANCE_OF_SELECTOR = Web3.keccak(text="balanceOf(address)")[:4].hex()
TOKEN0_SELECTOR = Web3.keccak(text="token0()")[:4].hex()
TOKEN1_SELECTOR = Web3.keccak(text="token1()")[:4].hex()


class UniswapV2DexProvider(DexProvider):
    """Query a Uniswap V2 factory/router deployment for token/WETH liquidity."""

    def __init__(
        self,
        web3: AsyncWeb3,
        *,
        name: str,
        factory_address: str,
        weth_address: str,
    ) -> None:
        self.name = name
        self._web3 = web3
        self._factory = AsyncWeb3.to_checksum_address(factory_address)
        self._weth = AsyncWeb3.to_checksum_address(weth_address)

    async def discover_pool(self, token_address: str) -> PoolDiscovery | None:
        token = AsyncWeb3.to_checksum_address(token_address)
        pair_address = await self._get_pair(token, self._weth)
        if pair_address is None:
            return None

        reserves = await self._get_reserves(pair_address)
        if reserves is None:
            return None

        reserve0, reserve1 = reserves
        if reserve0 == 0 and reserve1 == 0:
            return None

        token0 = await self._call_address(pair_address, TOKEN0_SELECTOR)
        token1 = await self._call_address(pair_address, TOKEN1_SELECTOR)
        if token0 is None or token1 is None:
            return None

        weth_reserve = reserve1 if token1.lower() == self._weth.lower() else reserve0
        liquidity_native = (weth_reserve / 10**18) * 2

        total_supply = await self._call_uint(pair_address, TOTAL_SUPPLY_SELECTOR) or 0
        burned = await self._balance_of(pair_address, DEAD_ADDRESS)
        zero_bal = await self._balance_of(pair_address, ZERO_ADDRESS)

        top_holder, top_balance = await self._resolve_top_lp_holder(
            pair_address,
            total_supply,
            burned,
            zero_bal,
        )

        return PoolDiscovery(
            dex_name=self.name,
            pair_address=pair_address.lower(),
            token0=token0.lower(),
            token1=token1.lower(),
            reserve0=reserve0,
            reserve1=reserve1,
            liquidity_native=liquidity_native,
            lp_total_supply=total_supply,
            lp_burned_balance=burned,
            lp_zero_balance=zero_bal,
            lp_top_holder=top_holder,
            lp_top_holder_balance=top_balance,
        )

    async def _get_pair(self, token_a: str, token_b: str) -> str | None:
        data = GET_PAIR_SELECTOR + encode(["address", "address"], [token_a, token_b]).hex()
        result = await self._eth_call(self._factory, bytes.fromhex(data))
        if result is None or len(result) < 32:
            return None
        address = "0x" + result[-20:].hex()
        if int(address, 16) == 0:
            return None
        return AsyncWeb3.to_checksum_address(address)

    async def _get_reserves(self, pair_address: str) -> tuple[int, int] | None:
        result = await self._eth_call(pair_address, bytes.fromhex(GET_RESERVES_SELECTOR))
        if result is None or len(result) < 64:
            return None
        reserve0 = int.from_bytes(result[0:32], byteorder="big")
        reserve1 = int.from_bytes(result[32:64], byteorder="big")
        return reserve0, reserve1

    async def _balance_of(self, token_address: str, holder: str) -> int:
        holder_checksum = AsyncWeb3.to_checksum_address(holder)
        data = BALANCE_OF_SELECTOR + encode(["address"], [holder_checksum]).hex()
        value = await self._call_uint(token_address, data)
        return value or 0

    async def _call_uint(self, target: str, selector_or_data: str) -> int | None:
        payload = (
            bytes.fromhex(selector_or_data)
            if not selector_or_data.startswith("0x")
            else bytes.fromhex(selector_or_data[2:])
        )
        result = await self._eth_call(target, payload)
        if result is None or len(result) < 32:
            return None
        return int.from_bytes(result[-32:], byteorder="big")

    async def _call_address(self, target: str, selector: str) -> str | None:
        result = await self._eth_call(target, bytes.fromhex(selector))
        if result is None or len(result) < 32:
            return None
        address = "0x" + result[-20:].hex()
        if int(address, 16) == 0:
            return None
        return AsyncWeb3.to_checksum_address(address)

    async def _eth_call(self, target: str, data: bytes) -> bytes | None:
        try:
            raw = await self._web3.eth.call({"to": target, "data": "0x" + data.hex()})
            return bytes(raw)
        except Exception:
            logger.debug("eth_call failed for %s", target, exc_info=True)
            return None

    async def _resolve_top_lp_holder(
        self,
        pair_address: str,
        total_supply: int,
        burned: int,
        zero_bal: int,
    ) -> tuple[str | None, int]:
        candidates = [
            (DEAD_ADDRESS, burned),
            (ZERO_ADDRESS, zero_bal),
        ]
        top_holder = None
        top_balance = 0
        for address, balance in candidates:
            if balance > top_balance:
                top_holder = address.lower()
                top_balance = balance
        if total_supply > 0 and top_balance == 0:
            return None, 0
        return top_holder, top_balance
