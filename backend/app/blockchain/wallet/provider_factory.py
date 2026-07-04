"""Factory helpers for wallet intelligence providers (M5.2)."""

from __future__ import annotations

from app.blockchain.wallet.explorer_wallet_provider import ExplorerWalletHistoryProvider
from app.blockchain.wallet.reputation_provider import WalletReputationProvider
from app.blockchain.wallet.static_reputation_provider import StaticWalletReputationProvider
from app.blockchain.wallet.wallet_history_provider import WalletHistoryProvider
from app.core.config import Settings


def create_wallet_history_provider(settings: Settings) -> WalletHistoryProvider | None:
    """Return an explorer wallet history provider when API key is configured."""
    if not settings.etherscan_api_key:
        return None
    return ExplorerWalletHistoryProvider(settings.etherscan_api_key)


def create_wallet_reputation_provider(_settings: Settings) -> WalletReputationProvider:
    """Return the default static reputation provider."""
    return StaticWalletReputationProvider()
