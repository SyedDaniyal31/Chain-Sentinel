"""Standards detector unit tests (M6.0)."""

from app.blockchain.protocol.standards_detector import detect_standards
from app.blockchain.token_standards import (
    ERC20_APPROVE_SELECTOR,
    ERC20_BALANCE_OF_SELECTOR,
    ERC20_TOTAL_SUPPLY_SELECTOR,
    ERC20_TRANSFER_SELECTOR,
    ERC721_OWNER_OF_SELECTOR,
    ERC721_TOKEN_URI_SELECTOR,
)


def test_detect_erc20_standard() -> None:
    bytecode = b"\x60\x80" + ERC20_TRANSFER_SELECTOR + ERC20_BALANCE_OF_SELECTOR + ERC20_TOTAL_SUPPLY_SELECTOR
    results = detect_standards(bytecode)
    standards = {item.standard.value for item in results if item.detected}
    assert "ERC20" in standards


def test_detect_erc721_standard() -> None:
    bytecode = b"\x60\x80" + ERC721_OWNER_OF_SELECTOR + ERC721_TOKEN_URI_SELECTOR
    results = detect_standards(bytecode)
    standards = {item.standard.value for item in results if item.detected}
    assert "ERC721" in standards


def test_detect_erc4626_standard() -> None:
    bytecode = b"\x60\x80" + bytes.fromhex("38d52e0f") + bytes.fromhex("6e553f65") + bytes.fromhex("01e1d114")
    results = detect_standards(bytecode)
    standards = {item.standard.value for item in results if item.detected}
    assert "ERC4626" in standards


def test_detect_standards_empty_bytecode() -> None:
    assert detect_standards(b"") == []
