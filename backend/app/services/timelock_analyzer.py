"""OpenZeppelin TimelockController detection via getMinDelay()."""

import logging

from web3 import AsyncWeb3

from app.blockchain.timelock import GET_MIN_DELAY_SELECTOR, parse_min_delay
from app.core.validators import normalize_eth_address
from app.schemas.scan_result import TimelockAnalysisData

logger = logging.getLogger(__name__)


class TimelockAnalyzer:
    """Detects TimelockController contracts and reads their minimum delay."""

    def __init__(self, web3: AsyncWeb3) -> None:
        self._web3 = web3

    async def analyze(self, contract_address: str) -> TimelockAnalysisData:
        """
        Attempt getMinDelay() on a contract address.

        Returns is_timelock=True when the call succeeds and yields a delay value.
        """
        normalized = normalize_eth_address(contract_address)
        checksum_address = AsyncWeb3.to_checksum_address(normalized)

        try:
            return_data = await self._web3.eth.call(
                {
                    "to": checksum_address,
                    "data": GET_MIN_DELAY_SELECTOR,
                }
            )
        except Exception:
            logger.info(
                "getMinDelay() unavailable for %s — not classified as timelock",
                normalized,
            )
            return TimelockAnalysisData(is_timelock=False, min_delay=None)

        min_delay = parse_min_delay(bytes(return_data))

        return TimelockAnalysisData(is_timelock=True, min_delay=min_delay)
