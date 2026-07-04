"""Token and vault standard detection for M6.0 protocol intelligence."""

from __future__ import annotations

from app.blockchain.protocol.models import ProtocolStandard, StandardDetection
from app.blockchain.token_standards import (
    ERC1155_BALANCE_OF_BATCH_SELECTOR,
    ERC1155_SAFE_TRANSFER_FROM_SELECTOR,
    ERC1155_URI_SELECTOR,
    ERC20_APPROVE_SELECTOR,
    ERC20_BALANCE_OF_SELECTOR,
    ERC20_TOTAL_SUPPLY_SELECTOR,
    ERC20_TRANSFER_FROM_SELECTOR,
    ERC20_TRANSFER_SELECTOR,
    ERC721_OWNER_OF_SELECTOR,
    ERC721_SAFE_TRANSFER_FROM_SELECTOR,
    ERC721_TOKEN_URI_SELECTOR,
    detect_token_standards_from_bytecode,
)

# ERC-4626 tokenized vault selectors.
ERC4626_ASSET_SELECTOR = bytes.fromhex("38d52e0f")
ERC4626_TOTAL_ASSETS_SELECTOR = bytes.fromhex("01e1d114")
ERC4626_DEPOSIT_SELECTOR = bytes.fromhex("6e553f65")
ERC4626_REDEEM_SELECTOR = bytes.fromhex("ba087652")


def detect_standards(bytecode: bytes) -> list[StandardDetection]:
    """Detect ERC-20/721/1155/4626 standards from runtime bytecode selectors."""
    if not bytecode:
        return []

    results: list[StandardDetection] = []
    token_flags = detect_token_standards_from_bytecode(bytecode)

    if token_flags.is_erc1155:
        results.append(
            StandardDetection(
                standard=ProtocolStandard.ERC1155,
                detected=True,
                reason="Bytecode exposes ERC-1155 batch transfer or URI selectors",
                confidence="high",
            )
        )
    elif _has_all(
        bytecode,
        (
            ERC1155_BALANCE_OF_BATCH_SELECTOR,
            ERC1155_SAFE_TRANSFER_FROM_SELECTOR,
        ),
    ):
        results.append(
            StandardDetection(
                standard=ProtocolStandard.ERC1155,
                detected=True,
                reason="Bytecode exposes ERC-1155 balanceOfBatch/safeTransferFrom selectors",
                confidence="medium",
            )
        )

    if token_flags.is_erc721:
        results.append(
            StandardDetection(
                standard=ProtocolStandard.ERC721,
                detected=True,
                reason="Bytecode exposes ERC-721 ownerOf or tokenURI selectors",
                confidence="high",
            )
        )
    elif _has_any(
        bytecode,
        (
            ERC721_OWNER_OF_SELECTOR,
            ERC721_SAFE_TRANSFER_FROM_SELECTOR,
            ERC721_TOKEN_URI_SELECTOR,
        ),
    ):
        results.append(
            StandardDetection(
                standard=ProtocolStandard.ERC721,
                detected=True,
                reason="Bytecode exposes ERC-721 NFT selectors",
                confidence="medium",
            )
        )

    if token_flags.is_erc20:
        results.append(
            StandardDetection(
                standard=ProtocolStandard.ERC20,
                detected=True,
                reason="Bytecode exposes ERC-20 transfer/balanceOf/totalSupply selectors",
                confidence="high",
            )
        )
    elif _has_erc20_selectors(bytecode):
        results.append(
            StandardDetection(
                standard=ProtocolStandard.ERC20,
                detected=True,
                reason="Bytecode exposes core ERC-20 transfer and balance selectors",
                confidence="medium",
            )
        )

    if _has_erc4626_selectors(bytecode):
        results.append(
            StandardDetection(
                standard=ProtocolStandard.ERC4626,
                detected=True,
                reason="Bytecode exposes ERC-4626 vault asset/deposit/totalAssets selectors",
                confidence="high" if _has_all(bytecode, (ERC4626_ASSET_SELECTOR, ERC4626_DEPOSIT_SELECTOR)) else "medium",
            )
        )

    return results


def _has_erc20_selectors(bytecode: bytes) -> bool:
    return (
        ERC20_TRANSFER_SELECTOR in bytecode
        and ERC20_BALANCE_OF_SELECTOR in bytecode
        and _has_any(
            bytecode,
            (
                ERC20_TOTAL_SUPPLY_SELECTOR,
                ERC20_APPROVE_SELECTOR,
                ERC20_TRANSFER_FROM_SELECTOR,
            ),
        )
    )


def _has_erc4626_selectors(bytecode: bytes) -> bool:
    hits = sum(
        1
        for selector in (
            ERC4626_ASSET_SELECTOR,
            ERC4626_TOTAL_ASSETS_SELECTOR,
            ERC4626_DEPOSIT_SELECTOR,
            ERC4626_REDEEM_SELECTOR,
        )
        if selector in bytecode
    )
    return hits >= 2


def _has_any(bytecode: bytes, selectors: tuple[bytes, ...]) -> bool:
    return any(selector in bytecode for selector in selectors)


def _has_all(bytecode: bytes, selectors: tuple[bytes, ...]) -> bool:
    return all(selector in bytecode for selector in selectors)
