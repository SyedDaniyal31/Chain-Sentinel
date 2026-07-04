"""Etherscan-compatible wallet history provider (M5.2)."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.blockchain.chain_registry import ChainRegistry, get_chain_registry
from app.blockchain.wallet.wallet_history_provider import ExplorerTransaction, WalletHistoryProvider

logger = logging.getLogger(__name__)


class ExplorerWalletHistoryProvider(WalletHistoryProvider):
    """Query Etherscan-compatible account endpoints for tx history."""

    def __init__(
        self,
        api_key: str,
        *,
        registry: ChainRegistry | None = None,
        timeout_seconds: int = 15,
    ) -> None:
        self._api_key = api_key
        self._registry = registry or get_chain_registry()
        self._timeout_seconds = timeout_seconds

    async def get_contract_creation(
        self,
        contract_address: str,
        chain_id: int,
    ) -> ExplorerTransaction | None:
        txs = await self._fetch_txlist(contract_address, chain_id, sort="asc", limit=1)
        if not txs:
            return None
        entry = txs[0]
        if str(entry.get("contractAddress") or "").lower() != contract_address.lower():
            return None
        return self._parse_tx(entry)

    async def get_wallet_transactions(
        self,
        wallet_address: str,
        chain_id: int,
        *,
        limit: int = 25,
    ) -> list[ExplorerTransaction]:
        txs = await self._fetch_txlist(wallet_address, chain_id, sort="asc", limit=limit)
        return [self._parse_tx(entry) for entry in txs]

    async def _fetch_txlist(
        self,
        address: str,
        chain_id: int,
        *,
        sort: str,
        limit: int,
    ) -> list[dict[str, Any]]:
        base_url = self._registry.get_explorer_api_base(chain_id)
        if base_url is None:
            return []

        params = {
            "module": "account",
            "action": "txlist",
            "address": address,
            "startblock": 0,
            "endblock": 99999999,
            "page": 1,
            "offset": limit,
            "sort": sort,
            "apikey": self._api_key,
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
                response = await client.get(base_url, params=params)
                response.raise_for_status()
                payload = response.json()
        except Exception:
            logger.debug(
                "Wallet txlist lookup failed for %s on chain %s",
                address,
                chain_id,
                exc_info=True,
            )
            return []

        if payload.get("status") != "1":
            return []

        results = payload.get("result")
        if not isinstance(results, list):
            return []
        return [entry for entry in results if isinstance(entry, dict)]

    @staticmethod
    def _parse_tx(entry: dict[str, Any]) -> ExplorerTransaction:
        return ExplorerTransaction(
            hash=str(entry.get("hash") or ""),
            from_address=str(entry.get("from") or "").lower(),
            to_address=(
                str(entry.get("to")).lower()
                if entry.get("to") not in (None, "", "0x")
                else None
            ),
            value_wei=int(entry.get("value") or 0),
            block_number=int(entry.get("blockNumber") or 0),
            timestamp=int(entry.get("timeStamp") or 0),
            is_error=str(entry.get("isError") or "0") == "1",
        )
