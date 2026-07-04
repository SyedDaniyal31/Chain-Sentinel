"""OpenZeppelin TimelockController helpers for eth_call discovery."""

# keccak256("getMinDelay()")[:4]
GET_MIN_DELAY_SELECTOR = "0x3ecaef56"


def parse_min_delay(return_data: bytes) -> int:
    """Decode a uint256 min delay (seconds) from a getMinDelay() return value."""
    word = bytes(return_data)
    if len(word) < 32:
        word = word.rjust(32, b"\x00")
    return int.from_bytes(word, byteorder="big")
