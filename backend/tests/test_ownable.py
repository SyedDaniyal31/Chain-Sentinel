"""Ownable helper unit tests."""

from app.blockchain.ownable import parse_ownable_owner


def test_parse_ownable_owner_returns_address() -> None:
    address = "0x1234567890123456789012345678901234567890"
    word = b"\x00" * 12 + bytes.fromhex(address[2:])

    assert parse_ownable_owner(word) == address


def test_parse_ownable_owner_returns_none_for_zero_address() -> None:
    assert parse_ownable_owner(b"\x00" * 32) is None
