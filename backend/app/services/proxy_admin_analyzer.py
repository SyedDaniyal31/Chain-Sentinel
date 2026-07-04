"""ProxyAdmin owner() tracing via eth_call."""

import logging

from web3 import AsyncWeb3

from app.blockchain.ownable import OWNER_FUNCTION_SELECTOR, parse_ownable_owner
from app.core.validators import normalize_eth_address
from app.models.enums import AdminType
from app.schemas.scan_result import ProxyAdminOwnerAnalysisData
from app.services.admin_classifier import AdminClassifier

logger = logging.getLogger(__name__)


class ProxyAdminAnalyzer:
    """Resolves the Ownable owner behind a contract-type upgrade admin (e.g. ProxyAdmin)."""

    def __init__(self, web3: AsyncWeb3, admin_classifier: AdminClassifier | None = None) -> None:
        self._web3 = web3
        self._admin_classifier = admin_classifier or AdminClassifier(web3)

    async def analyze(
        self,
        admin_address: str | None,
        admin_type: AdminType | None,
    ) -> ProxyAdminOwnerAnalysisData:
        """
        Attempt owner() on a contract admin and classify the resolved controller.

        Skips tracing when admin is absent, an EOA, or an identifiable multisig.
        """
        if admin_address is None or admin_type != AdminType.CONTRACT:
            return ProxyAdminOwnerAnalysisData(owner_address=None, owner_type=None)

        normalized_admin = normalize_eth_address(admin_address)
        checksum_admin = AsyncWeb3.to_checksum_address(normalized_admin)

        try:
            return_data = await self._web3.eth.call(
                {
                    "to": checksum_admin,
                    "data": OWNER_FUNCTION_SELECTOR,
                }
            )
        except Exception:
            logger.info(
                "owner() call unavailable for admin contract %s — skipping owner trace",
                normalized_admin,
            )
            return ProxyAdminOwnerAnalysisData(owner_address=None, owner_type=None)

        owner_address = parse_ownable_owner(bytes(return_data))
        if owner_address is None:
            return ProxyAdminOwnerAnalysisData(owner_address=None, owner_type=None)

        owner_type = await self._admin_classifier.classify(owner_address)

        return ProxyAdminOwnerAnalysisData(
            owner_address=owner_address,
            owner_type=owner_type,
        )
