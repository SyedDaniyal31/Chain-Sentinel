"""Yield vault protocol detection for M6.2 infrastructure intelligence."""

from __future__ import annotations

from dataclasses import dataclass

from app.blockchain.protocol.defi_registry import source_contains_marker
from app.blockchain.protocol.models import ProtocolDetectionContext, VaultDetectionResult
from app.blockchain.protocol.standards_detector import (
    ERC4626_ASSET_SELECTOR,
    ERC4626_DEPOSIT_SELECTOR,
    ERC4626_REDEEM_SELECTOR,
    ERC4626_TOTAL_ASSETS_SELECTOR,
)
from app.blockchain.protocol.vault_registry import match_vault_deployments

YEARN_PRICE_PER_SHARE = bytes.fromhex("99530b06")
BEEFY_STRATEGY = bytes.fromhex("a694fc3a")
PENDLE_SY = bytes.fromhex("3b180a38")
EIGEN_RESTAKE = bytes.fromhex("7b47c653")


@dataclass(frozen=True, slots=True)
class VaultSignatureProfile:
    name: str
    vault_type: str
    selectors: tuple[bytes, ...]
    source_markers: tuple[str, ...]
    requires_erc4626: bool = False


VAULT_SIGNATURE_PROFILES: tuple[VaultSignatureProfile, ...] = (
    VaultSignatureProfile(
        name="ERC4626",
        vault_type="ERC4626 Vault",
        selectors=(
            ERC4626_ASSET_SELECTOR,
            ERC4626_TOTAL_ASSETS_SELECTOR,
            ERC4626_DEPOSIT_SELECTOR,
            ERC4626_REDEEM_SELECTOR,
        ),
        source_markers=("ERC4626", "TOKENIZEDVAULT", "IERC4626"),
    ),
    VaultSignatureProfile(
        name="Yearn",
        vault_type="ERC4626 Vault",
        selectors=(YEARN_PRICE_PER_SHARE, ERC4626_DEPOSIT_SELECTOR, ERC4626_ASSET_SELECTOR),
        source_markers=("YEARN", "YVTOKEN", "IVAULT"),
        requires_erc4626=True,
    ),
    VaultSignatureProfile(
        name="Beefy",
        vault_type="Yield Vault",
        selectors=(BEEFY_STRATEGY, ERC4626_DEPOSIT_SELECTOR),
        source_markers=("BEEFY", "BEEFYVAULT", "ISTRATEGY"),
    ),
    VaultSignatureProfile(
        name="Pendle",
        vault_type="Yield Token",
        selectors=(PENDLE_SY, ERC4626_REDEEM_SELECTOR),
        source_markers=("PENDLE", "SYTOKEN", "IPENDLE"),
    ),
    VaultSignatureProfile(
        name="EigenLayer",
        vault_type="Restaking Vault",
        selectors=(EIGEN_RESTAKE,),
        source_markers=("EIGENLAYER", "STRATEGYMANAGER", "DELEGATIONMANAGER"),
    ),
)


def detect_vaults(context: ProtocolDetectionContext) -> list[VaultDetectionResult]:
    """Detect vault protocol integrations from registry, bytecode, and source."""
    if not context.bytecode and not context.logic_bytecode:
        return []

    results: dict[tuple[str, str], VaultDetectionResult] = {}
    bytecode = context.logic_bytecode or context.bytecode
    has_erc4626 = _has_erc4626(bytecode)

    for deployment in match_vault_deployments(context.chain_id, context.target_address):
        _upsert_result(
            results,
            VaultDetectionResult(
                name=deployment.protocol,
                type=deployment.vault_type,
                confidence=95,
            ),
        )

    for profile in VAULT_SIGNATURE_PROFILES:
        if profile.requires_erc4626 and not has_erc4626:
            continue

        selector_hits = sum(1 for selector in profile.selectors if selector in bytecode)
        if selector_hits == 0 and not source_contains_marker(context.verified_source_code, profile.source_markers):
            continue

        source_boost = 12 if source_contains_marker(context.verified_source_code, profile.source_markers) else 0
        verified_boost = 5 if context.is_verified and source_boost == 0 else 0
        score = min(100, 42 + selector_hits * 14 + source_boost + verified_boost)

        _upsert_result(
            results,
            VaultDetectionResult(name=profile.name, type=profile.vault_type, confidence=score),
        )

    return sorted(results.values(), key=lambda item: item.confidence, reverse=True)


def _has_erc4626(bytecode: bytes) -> bool:
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


def _upsert_result(
    results: dict[tuple[str, str], VaultDetectionResult],
    candidate: VaultDetectionResult,
) -> None:
    key = (candidate.name, candidate.type)
    existing = results.get(key)
    if existing is None or candidate.confidence > existing.confidence:
        results[key] = candidate
