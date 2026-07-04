"""EIP-1967 transparent proxy admin detection via storage slot reads."""

import logging

from web3 import AsyncWeb3

from app.blockchain.eip1967 import EIP1967_ADMIN_SLOT, parse_eip1967_admin
from app.core.exceptions import BlockchainRpcError
from app.core.validators import normalize_eth_address
from app.schemas.scan_result import AdminAnalysisData

logger = logging.getLogger(__name__)


class AdminAnalyzer:
    """Reads the EIP-1967 admin slot to identify upgrade authority on transparent proxies."""

    def __init__(self, web3: AsyncWeb3) -> None:
        self._web3 = web3

    async def analyze(self, target_address: str) -> AdminAnalysisData:
        """
        Read the EIP-1967 admin storage slot for a contract address.

        Raises:
            ValueError: Invalid address format.
            BlockchainRpcError: RPC failure during eth_getStorageAt.
        """
        normalized = normalize_eth_address(target_address)
        checksum_address = AsyncWeb3.to_checksum_address(normalized)

        try:
            storage_word = await self._web3.eth.get_storage_at(
                checksum_address,
                EIP1967_ADMIN_SLOT,
            )
        except Exception as exc:
            logger.exception("RPC admin storage read failed for %s", normalized)
            raise BlockchainRpcError("Ethereum RPC admin storage request failed") from exc

        admin_address = parse_eip1967_admin(bytes(storage_word))

        return AdminAnalysisData(admin_address=admin_address)
