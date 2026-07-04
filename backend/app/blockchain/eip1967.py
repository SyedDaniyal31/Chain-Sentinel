"""EIP-1967 proxy storage slot constants and parsing helpers."""

# keccak256("eip1967.proxy.implementation") - 1
EIP1967_IMPLEMENTATION_SLOT = (
    "0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc"
)

# keccak256("eip1967.proxy.admin") - 1
EIP1967_ADMIN_SLOT = (
    "0xb53127684a568b3173ae63b9f9a42cbe97166b21bf7da7747eed036fb0d46a55"
)

# keccak256("eip1967.proxy.beacon") - 1
EIP1967_BEACON_SLOT = (
    "0xa3f0ad74e5423aebfd80d3ef4346578335a9a72aeaee59ff6cb3582b35133d50"
)


def parse_eip1967_storage_address(storage_word: bytes) -> str | None:
    """
    Extract an address from a 32-byte EIP-1967 storage word.

    Returns a normalized lowercase address, or None when the slot is empty.
    """
    word = bytes(storage_word)
    if len(word) != 32:
        word = word.rjust(32, b"\x00")

    address_bytes = word[-20:]
    if address_bytes == b"\x00" * 20:
        return None

    return "0x" + address_bytes.hex()


def parse_eip1967_implementation(storage_word: bytes) -> str | None:
    """Extract an implementation address from the EIP-1967 implementation slot."""
    return parse_eip1967_storage_address(storage_word)


def parse_eip1967_admin(storage_word: bytes) -> str | None:
    """Extract an admin address from the EIP-1967 admin slot."""
    return parse_eip1967_storage_address(storage_word)
