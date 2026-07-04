"""Protocol family/name/type resolution for M6.0+ protocol intelligence."""

from __future__ import annotations

from app.blockchain.protocol.confidence_engine import resolve_confidence_level
from app.blockchain.protocol.defi_registry import STABLECOIN_NAME_MARKERS, source_contains_marker
from app.blockchain.protocol.models import (
    ProtocolDetectionBundle,
    ProtocolFamily,
    ProtocolFramework,
    ProtocolProxyKind,
    ProtocolStandard,
    ProtocolType,
)
from app.models.enums import ConfidenceLevel


def resolve_protocol_identity(bundle: ProtocolDetectionBundle) -> tuple[ProtocolFamily, str, ProtocolType]:
    """Derive protocol family, display name, and type from detector output."""
    if bundle.bridges:
        top = max(bundle.bridges, key=lambda item: item.confidence)
        slug = top.name.lower().replace(" ", "_")
        return ProtocolFamily.BRIDGE, f"{slug}_{top.role}", ProtocolType.UNKNOWN

    if bundle.dexes:
        top = max(bundle.dexes, key=lambda item: item.confidence)
        slug = top.name.lower().replace(" ", "_")
        if top.role == "pool":
            return ProtocolFamily.DEX, f"{slug}_pool", ProtocolType.UNKNOWN
        return ProtocolFamily.DEX, slug, ProtocolType.UNKNOWN

    if bundle.lending:
        top = max(bundle.lending, key=lambda item: item.confidence)
        slug = top.name.lower().replace(" ", "_")
        return ProtocolFamily.LENDING, f"{slug}_pool", ProtocolType.UNKNOWN

    if bundle.oracles:
        top = max(bundle.oracles, key=lambda item: item.confidence)
        slug = top.name.lower().replace(" ", "_")
        return ProtocolFamily.ORACLE, f"{slug}_feed", ProtocolType.UNKNOWN

    if bundle.vaults:
        top = max(bundle.vaults, key=lambda item: item.confidence)
        slug = top.name.lower().replace(" ", "_")
        return ProtocolFamily.VAULT, f"{slug}_vault", ProtocolType.TOKEN_VAULT

    if bundle.governance:
        top = max(bundle.governance, key=lambda item: item.confidence)
        slug = top.name.lower().replace(" ", "_")
        return ProtocolFamily.GOVERNANCE, slug, ProtocolType.GOVERNANCE

    if bundle.nfts:
        top = max(bundle.nfts, key=lambda item: item.confidence)
        if top.marketplace:
            slug = top.marketplace.lower().replace(" ", "_")
            return ProtocolFamily.NFT, f"{slug}_nft", ProtocolType.NON_FUNGIBLE_TOKEN
        standard_slug = top.standard.lower().replace(" ", "_")
        return ProtocolFamily.NFT, standard_slug, ProtocolType.NON_FUNGIBLE_TOKEN

    standards = {item.standard for item in bundle.standards if item.detected}
    frameworks = {item.framework for item in bundle.frameworks if item.detected}
    proxy = bundle.proxy.proxy_kind if bundle.proxy and bundle.proxy.detected else ProtocolProxyKind.NONE

    if _is_stablecoin(bundle, standards):
        return ProtocolFamily.STABLECOIN, _stablecoin_name(bundle), ProtocolType.FUNGIBLE_TOKEN

    if ProtocolStandard.ERC4626 in standards:
        return ProtocolFamily.VAULT, "erc4626_vault", ProtocolType.TOKEN_VAULT
    if ProtocolStandard.ERC1155 in standards:
        return ProtocolFamily.NFT, "erc1155_multi_token", ProtocolType.MULTI_TOKEN
    if ProtocolStandard.ERC721 in standards:
        return ProtocolFamily.NFT, "erc721_nft", ProtocolType.NON_FUNGIBLE_TOKEN
    if ProtocolStandard.ERC20 in standards:
        return ProtocolFamily.TOKEN, "erc20_token", ProtocolType.FUNGIBLE_TOKEN

    if ProtocolFramework.OPENZEPPELIN_TIMELOCK_CONTROLLER in frameworks:
        return ProtocolFamily.GOVERNANCE, "timelock_controller", ProtocolType.TIMELOCK

    if proxy == ProtocolProxyKind.MINIMAL_PROXY:
        return ProtocolFamily.PROXY, "eip1167_minimal_proxy", ProtocolType.MINIMAL_PROXY
    if proxy in {
        ProtocolProxyKind.TRANSPARENT,
        ProtocolProxyKind.UUPS,
        ProtocolProxyKind.BEACON,
        ProtocolProxyKind.ERC1967,
    }:
        label = {
            ProtocolProxyKind.TRANSPARENT: "transparent_proxy",
            ProtocolProxyKind.UUPS: "uups_proxy",
            ProtocolProxyKind.BEACON: "beacon_proxy",
            ProtocolProxyKind.ERC1967: "erc1967_proxy",
        }[proxy]
        return ProtocolFamily.PROXY, label, ProtocolType.UPGRADEABLE_PROXY

    if "Gnosis Safe" in bundle.integrations:
        return ProtocolFamily.GOVERNANCE, "gnosis_safe", ProtocolType.GOVERNANCE
    if "Uniswap V2 Pair" in bundle.integrations:
        return ProtocolFamily.DEX, "uniswap_v2_pool", ProtocolType.UNKNOWN

    if frameworks:
        return ProtocolFamily.GOVERNANCE, "openzeppelin_contract", ProtocolType.GOVERNANCE

    return ProtocolFamily.UNKNOWN, "unknown", ProtocolType.UNKNOWN


def resolve_confidence(bundle: ProtocolDetectionBundle) -> ConfidenceLevel:
    """Backward-compatible confidence level derived from evidence scoring."""
    return resolve_confidence_level(bundle)


def build_detection_reasons(bundle: ProtocolDetectionBundle) -> list[str]:
    """Flatten detector reasons into a stable ordered list."""
    reasons: list[str] = []
    for item in bundle.standards:
        if item.detected:
            reasons.append(item.reason)
    for item in bundle.frameworks:
        if item.detected:
            reasons.append(item.reason)
    if bundle.proxy and bundle.proxy.detected:
        reasons.append(bundle.proxy.reason)
    for integration in bundle.integrations:
        reasons.append(f"Integration detected: {integration}")
    for dex in bundle.dexes:
        reasons.append(f"DEX detected: {dex.name} ({dex.role}, confidence {dex.confidence})")
    for loan in bundle.lending:
        reasons.append(f"Lending detected: {loan.name} ({loan.role}, confidence {loan.confidence})")
    for oracle in bundle.oracles:
        reasons.append(f"Oracle detected: {oracle.name} (confidence {oracle.confidence})")
    for bridge in bundle.bridges:
        reasons.append(f"Bridge detected: {bridge.name} ({bridge.role}, confidence {bridge.confidence})")
    for vault in bundle.vaults:
        reasons.append(f"Vault detected: {vault.name} ({vault.type}, confidence {vault.confidence})")
    for nft in bundle.nfts:
        label = nft.marketplace or nft.standard
        reasons.append(f"NFT detected: {label} ({nft.standard}, confidence {nft.confidence})")
    for gov in bundle.governance:
        reasons.append(f"Governance detected: {gov.name} (confidence {gov.confidence})")
    return reasons


def _is_stablecoin(
    bundle: ProtocolDetectionBundle,
    standards: set[ProtocolStandard],
) -> bool:
    if ProtocolStandard.ERC20 not in standards:
        return False
    markers = STABLECOIN_NAME_MARKERS
    if source_contains_marker(bundle.verified_source_code, markers):
        return True
    contract_name = (bundle.contract_name or "").upper()
    return any(marker in contract_name for marker in markers)


def _stablecoin_name(bundle: ProtocolDetectionBundle) -> str:
    contract_name = (bundle.contract_name or "").upper()
    for marker in STABLECOIN_NAME_MARKERS:
        if marker in contract_name or source_contains_marker(bundle.verified_source_code, (marker,)):
            return f"{marker.lower()}_stablecoin"
    return "stablecoin"
