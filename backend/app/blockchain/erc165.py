"""EIP-165 interface identifiers and eth_call helpers."""

from web3 import Web3

# IERC165.supportsInterface(bytes4)
SUPPORTS_INTERFACE_SELECTOR = Web3.keccak(text="supportsInterface(bytes4)")[:4]

# Standard interface identifiers (XOR of inherited function selectors).
INTERFACE_ID_ERC165 = bytes.fromhex("01ffc9a7")
INTERFACE_ID_ERC721 = bytes.fromhex("80ac58cd")
INTERFACE_ID_ERC1155 = bytes.fromhex("d9b67a26")


def encode_supports_interface_call(interface_id: bytes) -> bytes:
    """ABI-encode supportsInterface(bytes4) calldata."""
    if len(interface_id) != 4:
        raise ValueError("interface_id must be 4 bytes")
    selector = SUPPORTS_INTERFACE_SELECTOR
    argument = interface_id.rjust(32, b"\x00")
    return selector + argument


def parse_supports_interface_result(return_data: bytes) -> bool:
    """Decode a standard bool return value from supportsInterface."""
    if len(return_data) < 32:
        return_data = return_data.rjust(32, b"\x00")
    return int.from_bytes(return_data[-32:], byteorder="big") != 0
