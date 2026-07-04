"""Token standard bytecode detection tests."""

from app.blockchain.token_standards import (
    ERC20_APPROVE_SELECTOR,
    ERC20_BALANCE_OF_SELECTOR,
    ERC20_TOTAL_SUPPLY_SELECTOR,
    ERC20_TRANSFER_SELECTOR,
    ERC721_OWNER_OF_SELECTOR,
    ERC1155_URI_SELECTOR,
    detect_token_standards_from_bytecode,
)


def test_detect_erc20_from_selectors() -> None:
    bytecode = (
        b"\x60\x80"
        + ERC20_TRANSFER_SELECTOR
        + ERC20_BALANCE_OF_SELECTOR
        + ERC20_TOTAL_SUPPLY_SELECTOR
        + ERC20_APPROVE_SELECTOR
    )
    flags = detect_token_standards_from_bytecode(bytecode)
    assert flags.is_erc20 is True
    assert flags.is_erc721 is False
    assert flags.is_erc1155 is False


def test_detect_erc721_before_erc20_when_owner_of_present() -> None:
    bytecode = b"\x60\x80" + ERC721_OWNER_OF_SELECTOR + ERC20_BALANCE_OF_SELECTOR
    flags = detect_token_standards_from_bytecode(bytecode)
    assert flags.is_erc721 is True
    assert flags.is_erc20 is False


def test_detect_erc1155_from_uri_selector() -> None:
    bytecode = b"\x60\x80" + ERC1155_URI_SELECTOR
    flags = detect_token_standards_from_bytecode(bytecode)
    assert flags.is_erc1155 is True
