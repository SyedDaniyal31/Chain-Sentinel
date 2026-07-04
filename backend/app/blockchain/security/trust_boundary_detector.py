"""Trust boundary detection for M6.4 threat surface intelligence."""

from __future__ import annotations

from app.blockchain.security.threat_models import ThreatSurfaceContext, TrustBoundary, TrustBoundaryKind


def detect_trust_boundaries(context: ThreatSurfaceContext) -> list[TrustBoundary]:
    """Detect security-relevant trust boundaries from scan intelligence."""
    boundaries: dict[tuple[str, str], TrustBoundary] = {}

    for oracle in context.oracles:
        name = str(oracle.get("name") or "Oracle")
        _upsert(
            boundaries,
            TrustBoundary(
                boundary_type=TrustBoundaryKind.ORACLE,
                label=name,
                confidence=int(oracle.get("confidence") or 80),
                detection_source="protocol_intelligence.oracles",
            ),
        )

    for bridge in context.bridges:
        name = str(bridge.get("name") or "Bridge")
        role = str(bridge.get("role") or "endpoint")
        _upsert(
            boundaries,
            TrustBoundary(
                boundary_type=TrustBoundaryKind.BRIDGE,
                label=f"{name} ({role})",
                confidence=int(bridge.get("confidence") or 82),
                detection_source="protocol_intelligence.bridges",
            ),
        )

    for vault in context.vaults:
        name = str(vault.get("name") or "Vault")
        _upsert(
            boundaries,
            TrustBoundary(
                boundary_type=TrustBoundaryKind.VAULT,
                label=name,
                confidence=int(vault.get("confidence") or 80),
                detection_source="protocol_intelligence.vaults",
            ),
        )

    for dex in context.dexes:
        name = str(dex.get("name") or "DEX")
        role = str(dex.get("role") or "router")
        boundary_type = TrustBoundaryKind.ROUTER if role == "router" else TrustBoundaryKind.ROUTER
        _upsert(
            boundaries,
            TrustBoundary(
                boundary_type=boundary_type,
                label=f"{name} ({role})",
                confidence=int(dex.get("confidence") or 78),
                detection_source="protocol_intelligence.dexes",
            ),
        )

    if context.liquidity_has_liquidity and context.liquidity_primary_dex:
        _upsert(
            boundaries,
            TrustBoundary(
                boundary_type=TrustBoundaryKind.ROUTER,
                label=context.liquidity_primary_dex,
                confidence=82,
                detection_source="liquidity_intelligence.primary_dex",
                address=context.liquidity_pair_address,
            ),
        )

    for gov in context.governance_protocols:
        name = str(gov.get("name") or "Governor")
        _upsert(
            boundaries,
            TrustBoundary(
                boundary_type=TrustBoundaryKind.GOVERNOR,
                label=name,
                confidence=int(gov.get("confidence") or 82),
                detection_source="protocol_intelligence.governance",
            ),
        )

    if context.has_timelock:
        _upsert(
            boundaries,
            TrustBoundary(
                boundary_type=TrustBoundaryKind.TIMELOCK,
                label="Timelock Controller",
                confidence=85,
                detection_source="governance_intelligence.timelock",
            ),
        )

    owner = context.wallet_owner or context.governance_ownership_address or context.owner_address
    if owner and not context.governance_ownership_renounced:
        _upsert(
            boundaries,
            TrustBoundary(
                boundary_type=TrustBoundaryKind.OWNER,
                label="Owner",
                confidence=86,
                detection_source="wallet_intelligence.owner",
                address=owner,
            ),
        )

    if context.wallet_treasury:
        _upsert(
            boundaries,
            TrustBoundary(
                boundary_type=TrustBoundaryKind.TREASURY,
                label="Treasury",
                confidence=84,
                detection_source="wallet_intelligence.treasury",
                address=context.wallet_treasury,
            ),
        )

    if context.treasury_is_multisig:
        _upsert(
            boundaries,
            TrustBoundary(
                boundary_type=TrustBoundaryKind.MULTISIG,
                label="Treasury Multisig",
                confidence=88,
                detection_source="wallet_intelligence.treasury_multisig",
                address=context.wallet_treasury,
            ),
        )

    if context.is_upgradeable or context.proxy_type not in {"none", "unknown"}:
        _upsert(
            boundaries,
            TrustBoundary(
                boundary_type=TrustBoundaryKind.UPGRADEABLE_PROXY,
                label=context.proxy_type if context.proxy_type not in {"none", "unknown"} else "upgradeable_proxy",
                confidence=87,
                detection_source="protocol_intelligence.proxy",
                address=context.implementation_address,
            ),
        )

    return sorted(boundaries.values(), key=lambda item: item.confidence, reverse=True)


def _upsert(
    boundaries: dict[tuple[str, str], TrustBoundary],
    candidate: TrustBoundary,
) -> None:
    key = (candidate.boundary_type.value, candidate.label.lower())
    existing = boundaries.get(key)
    if existing is None or candidate.confidence > existing.confidence:
        boundaries[key] = candidate
