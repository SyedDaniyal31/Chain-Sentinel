"""EIP-1967 upgradeable proxy detection via storage slot reads."""

import logging

from web3 import AsyncWeb3

from app.blockchain.eip1967 import EIP1967_IMPLEMENTATION_SLOT, parse_eip1967_implementation
from app.core.exceptions import BlockchainRpcError
from app.core.validators import normalize_eth_address
from app.schemas.scan_result import ProxyAnalysisData

logger = logging.getLogger(__name__)


class ProxyAnalyzer:
    """Detects EIP-1967 transparent/UUPS proxies by reading the implementation slot."""

    def __init__(self, web3: AsyncWeb3) -> None:
        self._web3 = web3

    async def analyze(self, target_address: str) -> ProxyAnalysisData:
        """
        Read the EIP-1967 implementation storage slot for a contract address.

        Raises:
            ValueError: Invalid address format.
            BlockchainRpcError: RPC failure during eth_getStorageAt.
        """
        normalized = normalize_eth_address(target_address)
        checksum_address = AsyncWeb3.to_checksum_address(normalized)

        try:
            storage_word = await self._web3.eth.get_storage_at(
                checksum_address,
                EIP1967_IMPLEMENTATION_SLOT,
            )
        except Exception as exc:
            logger.exception("RPC storage read failed for proxy %s", normalized)
            raise BlockchainRpcError("Ethereum RPC storage request failed") from exc

        implementation_address = parse_eip1967_implementation(bytes(storage_word))

        return ProxyAnalysisData(
            is_upgradeable=implementation_address is not None,
            implementation_address=implementation_address,
        )
