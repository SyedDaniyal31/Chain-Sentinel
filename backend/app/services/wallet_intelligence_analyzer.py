"""M5.2 contract wallet intelligence orchestrator."""

from __future__ import annotations

import logging

from app.blockchain.wallet.provider_factory import (
    create_wallet_history_provider,
    create_wallet_reputation_provider,
)
from app.blockchain.wallet.reputation_provider import WalletReputationProvider
from app.blockchain.wallet.wallet_history_provider import WalletHistoryProvider
from app.blockchain.wallet.wallet_intelligence import (
    WalletAnalysisContext,
    build_wallet_intelligence,
    empty_wallet_intelligence,
)
from app.core.config import Settings, get_settings
from app.core.validators import normalize_eth_address
from app.models.enums import AdminType, UpgradeAuthority
from app.schemas.scan_result import WalletIntelligenceData

logger = logging.getLogger(__name__)


class WalletIntelligenceAnalyzer:
    """
    Discover ownership, funding, reputation, and wallet relationships for contracts.

    Orchestrates explorer history and reputation providers using governance and
    liquidity context from ContractAnalyzer.
    """

    def __init__(
        self,
        chain_id: int,
        *,
        history_provider: WalletHistoryProvider | None = None,
        reputation_provider: WalletReputationProvider | None = None,
        settings: Settings | None = None,
    ) -> None:
        self._chain_id = chain_id
        config = settings or get_settings()
        self._history_provider = history_provider if history_provider is not None else (
            create_wallet_history_provider(config)
        )
        self._reputation_provider = reputation_provider or create_wallet_reputation_provider(config)

    async def analyze(
        self,
        contract_address: str,
        *,
        admin_address: str | None = None,
        admin_type: AdminType | None = None,
        owner_address: str | None = None,
        owner_type: AdminType | None = None,
        governance_ownership_address: str | None = None,
        is_timelock: bool = False,
        upgrade_authority: UpgradeAuthority | None = None,
        lp_owner: str | None = None,
    ) -> WalletIntelligenceData:
        normalized = normalize_eth_address(contract_address)
        context = WalletAnalysisContext(
            chain_id=self._chain_id,
            contract_address=normalized,
            admin_address=admin_address.lower() if admin_address else None,
            admin_type=admin_type,
            owner_address=owner_address.lower() if owner_address else None,
            owner_type=owner_type,
            governance_ownership_address=(
                governance_ownership_address.lower() if governance_ownership_address else None
            ),
            is_timelock=is_timelock,
            upgrade_authority=upgrade_authority,
            lp_owner=lp_owner.lower() if lp_owner else None,
        )

        if self._history_provider is None:
            logger.info("No wallet history provider configured for chain_id=%s", self._chain_id)
            return empty_wallet_intelligence()

        try:
            creation_tx = await self._history_provider.get_contract_creation(
                normalized,
                self._chain_id,
            )
            deployer = creation_tx.from_address if creation_tx else None
            deployer_transactions: list = []
            if deployer:
                deployer_transactions = await self._history_provider.get_wallet_transactions(
                    deployer,
                    self._chain_id,
                )

            reputation_target = deployer or governance_ownership_address or owner_address
            reputation_result = await self._reputation_provider.lookup(
                reputation_target or normalized,
                self._chain_id,
            )

            return build_wallet_intelligence(
                context,
                creation_tx=creation_tx,
                deployer_transactions=deployer_transactions,
                reputation_result=reputation_result,
            )
        except Exception:
            logger.debug(
                "Wallet intelligence analysis failed for %s",
                normalized,
                exc_info=True,
            )
            return empty_wallet_intelligence()
