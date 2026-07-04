"""NFT detector unit tests (M6.2)."""

from app.blockchain.protocol.models import ProtocolDetectionContext
from app.blockchain.protocol.nft_detector import detect_nfts
from app.blockchain.token_standards import ERC721_OWNER_OF_SELECTOR, ERC721_TOKEN_URI_SELECTOR


def test_detect_erc721_from_bytecode() -> None:
    bytecode = b"\x60\x80" + ERC721_OWNER_OF_SELECTOR + ERC721_TOKEN_URI_SELECTOR
    context = ProtocolDetectionContext(
        target_address="0x0000000000000000000000000000000000000001",
        bytecode=bytecode,
        logic_bytecode=bytecode,
    )
    results = detect_nfts(context)
    assert any(item.standard == "ERC721" and item.marketplace == "" for item in results)


def test_detect_erc2981_from_bytecode() -> None:
    bytecode = b"\x60\x80" + bytes.fromhex("2a55205a")
    context = ProtocolDetectionContext(
        target_address="0x0000000000000000000000000000000000000002",
        bytecode=bytecode,
        logic_bytecode=bytecode,
    )
    results = detect_nfts(context)
    assert any(item.standard == "ERC2981" for item in results)


def test_detect_opensea_from_source() -> None:
    bytecode = b"\x60\x80" + bytes.fromhex("b99a4dc5") + ERC721_OWNER_OF_SELECTOR
    context = ProtocolDetectionContext(
        target_address="0x0000000000000000000000000000000000000003",
        bytecode=bytecode,
        logic_bytecode=bytecode,
        verified_source_code="contract OperatorFilter is OpenSea registry {}",
    )
    results = detect_nfts(context)
    assert any(item.marketplace == "OpenSea" for item in results)


def test_detect_blur_from_source() -> None:
    bytecode = b"\x60\x80" + bytes.fromhex("e985e9c7") + ERC721_OWNER_OF_SELECTOR
    context = ProtocolDetectionContext(
        target_address="0x0000000000000000000000000000000000000004",
        bytecode=bytecode,
        logic_bytecode=bytecode,
        verified_source_code="contract BlurPool is IBlur marketplace {}",
    )
    results = detect_nfts(context)
    assert any(item.marketplace == "Blur" for item in results)
