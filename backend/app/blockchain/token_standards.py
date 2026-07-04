"""Token standard fingerprints for bytecode selector analysis."""

from dataclasses import dataclass

# ERC-20 core selectors.
ERC20_TRANSFER_SELECTOR = bytes.fromhex("a9059cbb")
ERC20_BALANCE_OF_SELECTOR = bytes.fromhex("70a08231")
ERC20_TOTAL_SUPPLY_SELECTOR = bytes.fromhex("18160ddd")
ERC20_APPROVE_SELECTOR = bytes.fromhex("095ea7b3")
ERC20_TRANSFER_FROM_SELECTOR = bytes.fromhex("23b872dd")

# ERC-721 distinctive selectors.
ERC721_OWNER_OF_SELECTOR = bytes.fromhex("6352211e")
ERC721_SAFE_TRANSFER_FROM_SELECTOR = bytes.fromhex("b88d4fde")
ERC721_TOKEN_URI_SELECTOR = bytes.fromhex("c87b56dd")

# ERC-1155 distinctive selectors.
ERC1155_BALANCE_OF_BATCH_SELECTOR = bytes.fromhex("4e1273f4")
ERC1155_SAFE_TRANSFER_FROM_SELECTOR = bytes.fromhex("f242432a")
ERC1155_URI_SELECTOR = bytes.fromhex("0e89341c")

# WETH-style wrapped native asset.
WETH_DEPOSIT_SELECTOR = bytes.fromhex("d0e30db0")
WETH_WITHDRAW_SELECTOR = bytes.fromhex("2e1a7d4d")


@dataclass(frozen=True, slots=True)
class TokenStandardFlags:
    """Heuristic token-standard detection from runtime bytecode."""

    is_erc20: bool = False
    is_erc721: bool = False
    is_erc1155: bool = False


def detect_token_standards_from_bytecode(bytecode: bytes) -> TokenStandardFlags:
    """
    Detect ERC-20 / ERC-721 / ERC-1155 via function selector presence.

    ERC-721 is checked before ERC-20 because both expose balanceOf(address).
    """
    if not bytecode:
        return TokenStandardFlags()

    is_erc1155 = _has_any(
        bytecode,
        (
            ERC1155_BALANCE_OF_BATCH_SELECTOR,
            ERC1155_SAFE_TRANSFER_FROM_SELECTOR,
            ERC1155_URI_SELECTOR,
        ),
    )
    if is_erc1155:
        return TokenStandardFlags(is_erc1155=True)

    is_erc721 = _has_any(
        bytecode,
        (
            ERC721_OWNER_OF_SELECTOR,
            ERC721_SAFE_TRANSFER_FROM_SELECTOR,
            ERC721_TOKEN_URI_SELECTOR,
        ),
    )
    if is_erc721:
        return TokenStandardFlags(is_erc721=True)

    has_transfer = ERC20_TRANSFER_SELECTOR in bytecode
    has_balance = ERC20_BALANCE_OF_SELECTOR in bytecode
    has_supply_or_allowance = _has_any(
        bytecode,
        (
            ERC20_TOTAL_SUPPLY_SELECTOR,
            ERC20_APPROVE_SELECTOR,
            ERC20_TRANSFER_FROM_SELECTOR,
            WETH_DEPOSIT_SELECTOR,
            WETH_WITHDRAW_SELECTOR,
        ),
    )
    is_erc20 = has_transfer and has_balance and has_supply_or_allowance

    return TokenStandardFlags(is_erc20=is_erc20)


def _has_any(bytecode: bytes, selectors: tuple[bytes, ...]) -> bool:
    return any(selector in bytecode for selector in selectors)
