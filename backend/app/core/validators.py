"""Shared input validators for API and blockchain layers."""

import re

ETH_ADDRESS_PATTERN = re.compile(r"^0x[a-fA-F0-9]{40}$", re.IGNORECASE)


def normalize_eth_address(address: str) -> str:
    """Validate and normalize an EVM address to lowercase hex."""
    normalized = address.strip()
    if not ETH_ADDRESS_PATTERN.fullmatch(normalized):
        raise ValueError(
            "target_address must be a valid 20-byte EVM address (0x + 40 hex characters)"
        )
    return normalized.lower()


def is_valid_eth_address(address: str) -> bool:
    """Return True when the value is a valid EVM address."""
    try:
        normalize_eth_address(address)
    except ValueError:
        return False
    return True
