"""Threat surface intelligence builder and scan context mapping (M6.4)."""

from __future__ import annotations

from app.blockchain.security.attack_surface_builder import build_threat_surface
from app.blockchain.security.threat_models import ThreatSurfaceContext
from app.schemas.scan_result import (
    AttackPathData,
    CriticalAssetData,
    DependencyGraphData,
    DependencyGraphEdgeData,
    DependencyGraphNodeData,
    ExternalDependencyData,
    PrivilegedEntityData,
    ProtocolIntelligenceData,
    ThreatSurfaceData,
    TrustBoundaryData,
)


def enrich_protocol_with_threat_surface(
    protocol: ProtocolIntelligenceData,
    context: ThreatSurfaceContext,
) -> ProtocolIntelligenceData:
    """Attach threat surface analysis to protocol intelligence payload."""
    result = build_threat_surface(context)
    threat_surface = ThreatSurfaceData(
        external_dependencies=[
            ExternalDependencyData(
                category=item.category.value,
                name=item.name,
                role=item.role,
                confidence=item.confidence,
                detection_source=item.detection_source,
                address=item.address,
            )
            for item in result.external_dependencies
        ],
        trust_boundaries=[
            TrustBoundaryData(
                boundary_type=item.boundary_type.value,
                label=item.label,
                confidence=item.confidence,
                detection_source=item.detection_source,
                address=item.address,
            )
            for item in result.trust_boundaries
        ],
        privileged_entities=[
            PrivilegedEntityData(
                entity_type=item.entity_type.value,
                label=item.label,
                confidence=item.confidence,
                detection_source=item.detection_source,
                address=item.address,
            )
            for item in result.privileged_entities
        ],
        attack_paths=[
            AttackPathData(
                name=item.name,
                steps=list(item.steps),
                confidence=item.confidence,
                detection_source=item.detection_source,
            )
            for item in result.attack_paths
        ],
        dependency_graph=DependencyGraphData(
            nodes=[
                DependencyGraphNodeData(
                    id=node.id,
                    label=node.label,
                    node_type=node.node_type,
                    address=node.address,
                )
                for node in result.dependency_graph.nodes
            ],
            edges=[
                DependencyGraphEdgeData(
                    source=edge.source,
                    target=edge.target,
                    relationship=edge.relationship,
                    confidence=edge.confidence,
                )
                for edge in result.dependency_graph.edges
            ],
        ),
        critical_assets=[
            CriticalAssetData(
                asset_type=item.asset_type,
                label=item.label,
                confidence=item.confidence,
                address=item.address,
            )
            for item in result.critical_assets
        ],
    )
    return protocol.model_copy(update={"threat_surface": threat_surface})


def build_threat_context_from_scan(
    *,
    target_address: str,
    protocol: ProtocolIntelligenceData,
    governance_type: object | None = None,
    upgrade_authority: object | None = None,
    governance_ownership_address: str | None = None,
    governance_ownership_renounced: bool = False,
    has_timelock: bool = False,
    is_verified: bool = False,
    is_upgradeable: bool = False,
    implementation_address: str | None = None,
    admin_address: str | None = None,
    owner_address: str | None = None,
    capabilities_detail: dict | None = None,
    mint_capability: bool = False,
    pause_capability: bool = False,
    honeypot_is_suspected: bool = False,
    honeypot_is_confirmed: bool = False,
    liquidity_has_liquidity: bool = False,
    liquidity_primary_dex: str | None = None,
    liquidity_pair_address: str | None = None,
    liquidity_usd: object | None = None,
    wallet_creator: str | None = None,
    wallet_deployer: str | None = None,
    wallet_owner: str | None = None,
    wallet_treasury: str | None = None,
    treasury_is_multisig: bool = False,
) -> ThreatSurfaceContext:
    """Map scan analyzer outputs into a threat surface analysis context."""
    capability_controllers: list[tuple[str, str]] = []
    for name, detail in (capabilities_detail or {}).items():
        controller = getattr(detail, "controller", None) if detail is not None else None
        enabled = getattr(detail, "enabled", False) if detail is not None else False
        if enabled and controller:
            capability_controllers.append((name, controller))

    def _dump_items(items: list) -> list[dict]:
        return [item.model_dump() if hasattr(item, "model_dump") else dict(item) for item in items]

    return ThreatSurfaceContext(
        target_address=target_address,
        protocol_family=protocol.protocol_family,
        proxy_type=protocol.proxy_type,
        is_upgradeable=is_upgradeable,
        is_verified=is_verified,
        implementation_address=implementation_address,
        admin_address=admin_address,
        owner_address=owner_address,
        governance_type=_enum_value(governance_type),
        upgrade_authority=_enum_value(upgrade_authority),
        governance_ownership_address=governance_ownership_address,
        governance_ownership_renounced=governance_ownership_renounced,
        has_timelock=has_timelock,
        treasury_is_multisig=treasury_is_multisig,
        dexes=_dump_items(protocol.dexes),
        lending=_dump_items(protocol.lending),
        oracles=_dump_items(protocol.oracles),
        bridges=_dump_items(protocol.bridges),
        vaults=_dump_items(protocol.vaults),
        governance_protocols=_dump_items(protocol.governance),
        relationships=[item.model_dump() for item in protocol.relationships],
        liquidity_has_liquidity=liquidity_has_liquidity,
        liquidity_primary_dex=liquidity_primary_dex,
        liquidity_pair_address=liquidity_pair_address,
        liquidity_usd=str(liquidity_usd) if liquidity_usd is not None else None,
        wallet_creator=wallet_creator,
        wallet_deployer=wallet_deployer,
        wallet_owner=wallet_owner or owner_address,
        wallet_treasury=wallet_treasury,
        capability_controllers=capability_controllers,
        mint_capability=mint_capability,
        pause_capability=pause_capability,
        honeypot_is_suspected=honeypot_is_suspected,
        honeypot_is_confirmed=honeypot_is_confirmed,
    )


def _enum_value(value: object | None) -> str | None:
    if value is None:
        return None
    return str(getattr(value, "value", value))
