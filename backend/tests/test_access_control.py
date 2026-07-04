"""AccessControl helper unit tests."""

from web3 import Web3

from app.blockchain.access_control import (
    BURNER_ROLE,
    DEFAULT_ADMIN_ROLE,
    GET_ROLE_ADMIN_SELECTOR,
    HAS_ROLE_SELECTOR,
    KNOWN_ROLES,
    MINTER_ROLE,
    PAUSER_ROLE,
    encode_get_role_admin_call,
    encode_has_role_call,
    has_access_control_selectors,
    parse_has_role_result,
    parse_role_admin,
    role_id_hex,
    role_name_for_id,
)

ACCOUNT = "0x1234567890123456789012345678901234567890"


def test_known_roles_include_standard_oz_labels() -> None:
    assert set(KNOWN_ROLES) == {
        "DEFAULT_ADMIN_ROLE",
        "MINTER_ROLE",
        "PAUSER_ROLE",
        "UPGRADER_ROLE",
        "BURNER_ROLE",
    }


def test_role_id_hex_formats_bytes32() -> None:
    assert role_id_hex(DEFAULT_ADMIN_ROLE) == "0x" + "00" * 32
    assert role_id_hex(MINTER_ROLE).startswith("0x")
    assert len(role_id_hex(MINTER_ROLE)) == 66


def test_encode_get_role_admin_call() -> None:
    calldata = encode_get_role_admin_call(MINTER_ROLE)
    assert calldata[:4] == GET_ROLE_ADMIN_SELECTOR
    assert calldata[4:36] == MINTER_ROLE


def test_encode_has_role_call() -> None:
    calldata = encode_has_role_call(PAUSER_ROLE, ACCOUNT)
    assert calldata[:4] == HAS_ROLE_SELECTOR
    assert calldata[4:36] == PAUSER_ROLE
    assert calldata[48:68] == bytes.fromhex(ACCOUNT[2:])


def test_parse_role_admin() -> None:
    admin = parse_role_admin(DEFAULT_ADMIN_ROLE)
    assert admin == DEFAULT_ADMIN_ROLE


def test_parse_has_role_result() -> None:
    assert parse_has_role_result(b"\x00" * 31 + b"\x01") is True
    assert parse_has_role_result(b"\x00" * 32) is False


def test_has_access_control_selectors() -> None:
    bytecode = b"\x60\x80" + GET_ROLE_ADMIN_SELECTOR + HAS_ROLE_SELECTOR
    assert has_access_control_selectors(bytecode) is True
    assert has_access_control_selectors(b"\x60\x80") is False


def test_role_name_for_id_round_trip() -> None:
    assert role_name_for_id(BURNER_ROLE) == "BURNER_ROLE"
    assert role_name_for_id(Web3.keccak(text="UNKNOWN_ROLE")) is None
