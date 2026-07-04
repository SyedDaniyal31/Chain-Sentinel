"""NFT protocol and marketplace detection for M6.2 infrastructure intelligence."""

from __future__ import annotations

from dataclasses import dataclass

from app.blockchain.protocol.defi_registry import source_contains_marker
from app.blockchain.protocol.models import NftDetectionResult, ProtocolDetectionContext
from app.blockchain.token_standards import (
    ERC1155_BALANCE_OF_BATCH_SELECTOR,
    ERC1155_SAFE_TRANSFER_FROM_SELECTOR,
    ERC721_OWNER_OF_SELECTOR,
    ERC721_SAFE_TRANSFER_FROM_SELECTOR,
    ERC721_TOKEN_URI_SELECTOR,
)

ERC2981_ROYALTY = bytes.fromhex("2a55205a")
OPENSEA_OPERATOR = bytes.fromhex("b99a4dc5")
BLUR_MARKETPLACE = bytes.fromhex("e985e9c7")


@dataclass(frozen=True, slots=True)
class NftSignatureProfile:
    standard: str
    marketplace: str
    selectors: tuple[bytes, ...]
    source_markers: tuple[str, ...]


NFT_SIGNATURE_PROFILES: tuple[NftSignatureProfile, ...] = (
    NftSignatureProfile(
        standard="ERC721",
        marketplace="",
        selectors=(ERC721_OWNER_OF_SELECTOR, ERC721_SAFE_TRANSFER_FROM_SELECTOR, ERC721_TOKEN_URI_SELECTOR),
        source_markers=("ERC721", "IERC721", "NONFUNGIBLETOKEN"),
    ),
    NftSignatureProfile(
        standard="ERC1155",
        marketplace="",
        selectors=(ERC1155_BALANCE_OF_BATCH_SELECTOR, ERC1155_SAFE_TRANSFER_FROM_SELECTOR),
        source_markers=("ERC1155", "IERC1155", "MULTITOKEN"),
    ),
    NftSignatureProfile(
        standard="ERC2981",
        marketplace="",
        selectors=(ERC2981_ROYALTY,),
        source_markers=("ERC2981", "ROYALTYINFO", "NFTROYALTY"),
    ),
    NftSignatureProfile(
        standard="ERC721",
        marketplace="OpenSea",
        selectors=(OPENSEA_OPERATOR, ERC721_OWNER_OF_SELECTOR),
        source_markers=("OPERATORFILTER", "OPENSEA", "IOperatorFilterRegistry"),
    ),
    NftSignatureProfile(
        standard="ERC721",
        marketplace="Blur",
        selectors=(BLUR_MARKETPLACE, ERC721_OWNER_OF_SELECTOR),
        source_markers=("BLUR", "BLURPOOL", "IBLUR"),
    ),
)


def detect_nfts(context: ProtocolDetectionContext) -> list[NftDetectionResult]:
    """Detect NFT standards and marketplace integrations from bytecode and source."""
    if not context.bytecode and not context.logic_bytecode:
        return []

    results: dict[tuple[str, str], NftDetectionResult] = {}
    bytecode = context.logic_bytecode or context.bytecode

    for profile in NFT_SIGNATURE_PROFILES:
        selector_hits = sum(1 for selector in profile.selectors if selector in bytecode)
        if selector_hits == 0 and not source_contains_marker(context.verified_source_code, profile.source_markers):
            continue

        source_boost = 12 if source_contains_marker(context.verified_source_code, profile.source_markers) else 0
        verified_boost = 5 if context.is_verified and source_boost == 0 else 0
        score = min(100, 38 + selector_hits * 16 + source_boost + verified_boost)

        _upsert_result(
            results,
            NftDetectionResult(
                standard=profile.standard,
                marketplace=profile.marketplace,
                confidence=score,
            ),
        )

    return sorted(results.values(), key=lambda item: item.confidence, reverse=True)


def _upsert_result(
    results: dict[tuple[str, str], NftDetectionResult],
    candidate: NftDetectionResult,
) -> None:
    key = (candidate.standard, candidate.marketplace)
    existing = results.get(key)
    if existing is None or candidate.confidence > existing.confidence:
        results[key] = candidate
