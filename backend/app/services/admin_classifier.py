"""Upgrade admin address classification via eth_getCode."""

import logging

from web3 import AsyncWeb3

from app.blockchain.multisig import is_gnosis_safe_multisig
from app.core.exceptions import BlockchainRpcError
from app.core.validators import normalize_eth_address
from app.models.enums import AdminType

logger = logging.getLogger(__name__)


class AdminClassifier:
    """Classifies an upgrade admin address as EOA, contract, or identifiable multisig."""

    def __init__(self, web3: AsyncWeb3) -> None:
        self._web3 = web3

    async def classify(self, admin_address: str | None) -> AdminType | None:
        """
        Determine admin wallet type using runtime bytecode at the admin address.

        Returns None when no admin address was resolved from the proxy slot.
        """
        if admin_address is None:
            return None

        normalized = normalize_eth_address(admin_address)
        checksum_address = AsyncWeb3.to_checksum_address(normalized)

        try:
            bytecode = await self._web3.eth.get_code(checksum_address)
        except Exception as exc:
            logger.exception("RPC getCode failed for admin %s", normalized)
            raise BlockchainRpcError("Ethereum RPC admin classification request failed") from exc

        bytecode_bytes = bytes(bytecode)
        if len(bytecode_bytes) == 0:
            return AdminType.EOA

        if is_gnosis_safe_multisig(bytecode_bytes):
            return AdminType.MULTISIG

        return AdminType.CONTRACT
