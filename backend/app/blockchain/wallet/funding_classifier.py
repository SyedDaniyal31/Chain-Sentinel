"""Funding source classification for deployer wallets (M5.2)."""

from __future__ import annotations

import time

from app.blockchain.wallet.wallet_history_provider import ExplorerTransaction
from app.models.enums import FundingSourceType

FRESH_WALLET_MAX_AGE_SECONDS = 30 * 24 * 3600
FRESH_WALLET_MAX_TX_COUNT = 5

EXCHANGE_ADDRESSES: frozenset[str] = frozenset(
    address.lower()
    for address in (
        "0x28c6c06298d014dbb8898931c1fbd413e3765460",  # Binance 14
        "0x21a31ee1afc51d94c2efccaa2092ad1028285549",  # Binance 15
        "0xdfd5293d8e347dfe59e90efd55b2956a1343963d",  # Binance 16
        "0x56eddb7aa87536c081ccc0267460e1c497a776bf",  # Coinbase 1
        "0x71660c4005ba85c37ccec55d0c9893ddbf8fe432",  # Kraken 13
    )
)

BRIDGE_ADDRESSES: frozenset[str] = frozenset(
    address.lower()
    for address in (
        "0x3154cf16ccdb4c6d922629664174b904d80f70c41",  # Base bridge
        "0x8315177ab297ba92a06054ce5a76494a1688eaab",  # Arbitrum bridge
    )
)

TORNADO_ADDRESSES: frozenset[str] = frozenset(
    address.lower()
    for address in (
        "0x8589427373d6d57e722938443819027f913358bb",
        "0xd90e2f925ba723939877147291111569bc6c9620",
        "0x722122dfeb585d0a4c494276170a0f9620b2e470",
        "0x12d66f87a04a9e220743712ce6d9bb1b5616b8fc",
    )
)

MIXER_ADDRESSES: frozenset[str] = frozenset(TORNADO_ADDRESSES)


def classify_funding_source(funder_address: str | None) -> FundingSourceType:
    """Map a funding wallet to a coarse source category."""
    if funder_address is None:
        return FundingSourceType.UNKNOWN

    normalized = funder_address.lower()
    if normalized in TORNADO_ADDRESSES:
        return FundingSourceType.TORNADO
    if normalized in MIXER_ADDRESSES:
        return FundingSourceType.MIXER
    if normalized in EXCHANGE_ADDRESSES:
        return FundingSourceType.EXCHANGE
    if normalized in BRIDGE_ADDRESSES:
        return FundingSourceType.BRIDGE
    return FundingSourceType.EOA


def find_first_inbound_funding(
    wallet_address: str,
    transactions: list[ExplorerTransaction],
) -> ExplorerTransaction | None:
    """Return the earliest inbound native transfer to the wallet."""
    normalized = wallet_address.lower()
    inbound = [
        tx
        for tx in transactions
        if tx.to_address == normalized and tx.value_wei > 0 and not tx.is_error
    ]
    if not inbound:
        return None
    return min(inbound, key=lambda tx: (tx.block_number, tx.timestamp))


def is_fresh_wallet(
    transactions: list[ExplorerTransaction],
    *,
    now_timestamp: int | None = None,
) -> bool:
    """Heuristic fresh-wallet detection based on age and activity."""
    if not transactions:
        return True
    if len(transactions) <= FRESH_WALLET_MAX_TX_COUNT:
        return True

    now = now_timestamp or int(time.time())
    first_ts = min(tx.timestamp for tx in transactions if tx.timestamp > 0)
    if first_ts <= 0:
        return len(transactions) <= FRESH_WALLET_MAX_TX_COUNT
    return (now - first_ts) <= FRESH_WALLET_MAX_AGE_SECONDS
