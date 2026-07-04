"""Wallet on-chain analysis via JSON-RPC."""

import logging

from web3 import AsyncWeb3

from app.core.exceptions import BlockchainRpcError
from app.core.validators import normalize_eth_address
from app.schemas.scan_result import WalletAnalysisData

logger = logging.getLogger(__name__)


class WalletAnalyzer:
    """Collects baseline wallet intelligence from an EVM JSON-RPC endpoint."""

    def __init__(self, web3: AsyncWeb3, expected_chain_id: int | None = None) -> None:
        self._web3 = web3
        self._expected_chain_id = expected_chain_id

    async def analyze(self, target_address: str) -> WalletAnalysisData:
        """
        Fetch chain context and native balance for a wallet address.

        Raises:
            ValueError: Invalid address format.
            BlockchainRpcError: RPC connectivity or chain mismatch.
        """
        normalized = normalize_eth_address(target_address)
        checksum_address = AsyncWeb3.to_checksum_address(normalized)

        if not await self._web3.is_connected():
            raise BlockchainRpcError("Unable to connect to Ethereum RPC endpoint")

        try:
            chain_id = await self._web3.eth.chain_id
            latest_block = await self._web3.eth.block_number
            wallet_balance_wei = await self._web3.eth.get_balance(checksum_address)
        except Exception as exc:
            logger.exception("RPC call failed for wallet %s", normalized)
            raise BlockchainRpcError("Ethereum RPC request failed") from exc

        if self._expected_chain_id is not None and chain_id != self._expected_chain_id:
            raise BlockchainRpcError(
                f"RPC chain_id {chain_id} does not match configured CHAIN_ID {self._expected_chain_id}"
            )

        return WalletAnalysisData(
            chain_id=chain_id,
            latest_block=latest_block,
            wallet_balance_wei=wallet_balance_wei,
        )
