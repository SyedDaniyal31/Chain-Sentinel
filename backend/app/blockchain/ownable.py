"""OpenZeppelin Ownable pattern helpers for eth_call discovery."""

# keccak256("owner()")[:4]
OWNER_FUNCTION_SELECTOR = "0x8da5cb5b"


def parse_ownable_owner(return_data: bytes) -> str | None:
    """
    Decode an address from a standard owner() eth_call return value.

    Returns a normalized lowercase address, or None when empty or malformed.
    """
    if len(return_data) < 32:
        return_data = return_data.rjust(32, b"\x00")

    address_bytes = return_data[-20:]
    if address_bytes == b"\x00" * 20:
        return None

    return "0x" + address_bytes.hex()
