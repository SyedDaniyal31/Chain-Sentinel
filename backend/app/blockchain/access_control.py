"""OpenZeppelin AccessControl role constants and eth_call helpers."""

from web3 import Web3

# IERC20AccessControl function selectors.
GET_ROLE_ADMIN_SELECTOR = Web3.keccak(text="getRoleAdmin(bytes32)")[:4]
HAS_ROLE_SELECTOR = Web3.keccak(text="hasRole(bytes32,address)")[:4]

# Standard OpenZeppelin role identifiers.
DEFAULT_ADMIN_ROLE = b"\x00" * 32
MINTER_ROLE = Web3.keccak(text="MINTER_ROLE")
PAUSER_ROLE = Web3.keccak(text="PAUSER_ROLE")
UPGRADER_ROLE = Web3.keccak(text="UPGRADER_ROLE")
BURNER_ROLE = Web3.keccak(text="BURNER_ROLE")

KNOWN_ROLES: dict[str, bytes] = {
    "DEFAULT_ADMIN_ROLE": DEFAULT_ADMIN_ROLE,
    "MINTER_ROLE": MINTER_ROLE,
    "PAUSER_ROLE": PAUSER_ROLE,
    "UPGRADER_ROLE": UPGRADER_ROLE,
    "BURNER_ROLE": BURNER_ROLE,
}

ROLE_ID_TO_NAME: dict[bytes, str] = {role_id: name for name, role_id in KNOWN_ROLES.items()}


def role_id_hex(role_id: bytes) -> str:
    """Return a normalized 0x-prefixed bytes32 hex string."""
    return "0x" + role_id.hex()


def encode_get_role_admin_call(role_id: bytes) -> bytes:
    """ABI-encode getRoleAdmin(bytes32) calldata."""
    if len(role_id) != 32:
        raise ValueError("role_id must be 32 bytes")
    return GET_ROLE_ADMIN_SELECTOR + role_id


def encode_has_role_call(role_id: bytes, account: str) -> bytes:
    """ABI-encode hasRole(bytes32,address) calldata."""
    if len(role_id) != 32:
        raise ValueError("role_id must be 32 bytes")
    account_bytes = bytes.fromhex(account[2:] if account.startswith("0x") else account)
    if len(account_bytes) != 20:
        raise ValueError("account must be 20 bytes")
    account_word = account_bytes.rjust(32, b"\x00")
    return HAS_ROLE_SELECTOR + role_id + account_word


def parse_role_admin(return_data: bytes) -> bytes:
    """Decode bytes32 admin role from getRoleAdmin() return data."""
    word = bytes(return_data)
    if len(word) < 32:
        word = word.rjust(32, b"\x00")
    return word[-32:]


def parse_has_role_result(return_data: bytes) -> bool:
    """Decode bool from hasRole() return data."""
    word = bytes(return_data)
    if len(word) < 32:
        word = word.rjust(32, b"\x00")
    return int.from_bytes(word[-32:], byteorder="big") != 0


def has_access_control_selectors(bytecode: bytes) -> bool:
    """Return True when runtime bytecode exposes AccessControl selectors."""
    return GET_ROLE_ADMIN_SELECTOR in bytecode and HAS_ROLE_SELECTOR in bytecode


def role_name_for_id(role_id: bytes) -> str | None:
    """Map a bytes32 role id to a known label when available."""
    return ROLE_ID_TO_NAME.get(role_id)
