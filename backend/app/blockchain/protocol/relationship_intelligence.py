"""Cross-protocol relationship intelligence builder (M6.3)."""

from __future__ import annotations

from app.blockchain.protocol.architecture_graph import build_architecture_graph, build_architecture_summary
from app.blockchain.protocol.relationship_builder import build_relationship_candidates
from app.blockchain.protocol.relationship_engine import merge_duplicate_wallet_relationships, normalize_relationships
from app.blockchain.protocol.relationship_models import RelationshipAnalysisContext
from app.schemas.scan_result import (
    ArchitectureGraphData,
    ArchitectureGraphEdgeData,
    ArchitectureGraphNodeData,
    ArchitectureSummaryData,
    ProtocolIntelligenceData,
    ProtocolRelationshipData,
)


def enrich_protocol_intelligence(
    protocol: ProtocolIntelligenceData,
    context: RelationshipAnalysisContext,
) -> ProtocolIntelligenceData:
    """Extend protocol intelligence with relationships, graph, and summary."""
    if not context.target_address:
        return protocol

    candidates = build_relationship_candidates(context)
    relationships = merge_duplicate_wallet_relationships(normalize_relationships(candidates))
    graph = build_architecture_graph(context, candidates, relationships)
    summary = build_architecture_summary(context, relationships)

    return protocol.model_copy(
        update={
            "relationships": [
                ProtocolRelationshipData(
                    source=item.source,
                    target=item.target,
                    relationship_type=item.relationship_type.value,
                    confidence=item.confidence,
                    detection_source=item.detection_source,
                )
                for item in relationships
            ],
            "architecture_graph": ArchitectureGraphData(
                nodes=[
                    ArchitectureGraphNodeData(
                        id=node.id,
                        label=node.label,
                        node_type=node.node_type,
                        address=node.address,
                    )
                    for node in graph.nodes
                ],
                edges=[
                    ArchitectureGraphEdgeData(
                        source=edge.source,
                        target=edge.target,
                        relationship=edge.relationship,
                        confidence=edge.confidence,
                        detection_source=edge.detection_source,
                    )
                    for edge in graph.edges
                ],
            ),
            "architecture_summary": ArchitectureSummaryData(
                application_type=summary.application_type,
                protocol_stack=summary.protocol_stack,
                oracle=summary.oracle,
                liquidity=summary.liquidity,
                bridge=summary.bridge,
                governance=summary.governance,
                upgradeability=summary.upgradeability,
                ownership=summary.ownership,
            ),
        }
    )


def build_relationship_context_from_scan(
    *,
    target_address: str,
    protocol: ProtocolIntelligenceData,
    governance_type: str | None = None,
    upgrade_authority: str | None = None,
    governance_ownership_address: str | None = None,
    governance_ownership_renounced: bool = False,
    has_timelock: bool = False,
    is_verified: bool = False,
    is_upgradeable: bool = False,
    implementation_address: str | None = None,
    admin_address: str | None = None,
    owner_address: str | None = None,
    capabilities_detail: dict | None = None,
    honeypot_is_suspected: bool = False,
    liquidity_has_liquidity: bool = False,
    liquidity_primary_dex: str | None = None,
    liquidity_pair_address: str | None = None,
    wallet_creator: str | None = None,
    wallet_deployer: str | None = None,
    wallet_owner: str | None = None,
    wallet_treasury: str | None = None,
) -> RelationshipAnalysisContext:
    """Map scan analyzer outputs into a relationship analysis context."""
    capability_controllers: list[tuple[str, str]] = []
    for name, detail in (capabilities_detail or {}).items():
        controller = getattr(detail, "controller", None) if detail is not None else None
        enabled = getattr(detail, "enabled", False) if detail is not None else False
        if enabled and controller:
            capability_controllers.append((name, controller))

    def _dump_items(items: list) -> list[dict]:
        return [item.model_dump() if hasattr(item, "model_dump") else dict(item) for item in items]

    return RelationshipAnalysisContext(
        target_address=target_address,
        protocol_family=protocol.protocol_family,
        protocol_name=protocol.protocol_name,
        protocol_type=protocol.protocol_type,
        proxy_type=protocol.proxy_type,
        is_verified=is_verified,
        is_upgradeable=is_upgradeable,
        implementation_address=implementation_address,
        admin_address=admin_address,
        owner_address=owner_address,
        governance_type=_enum_value(governance_type),
        upgrade_authority=_enum_value(upgrade_authority),
        governance_ownership_address=governance_ownership_address,
        governance_ownership_renounced=governance_ownership_renounced,
        has_timelock=has_timelock,
        dexes=_dump_items(protocol.dexes),
        lending=_dump_items(protocol.lending),
        oracles=_dump_items(protocol.oracles),
        bridges=_dump_items(protocol.bridges),
        vaults=_dump_items(protocol.vaults),
        nfts=_dump_items(protocol.nfts),
        governance_protocols=_dump_items(protocol.governance),
        integrations=list(protocol.integrations),
        standards=list(protocol.standards),
        liquidity_has_liquidity=liquidity_has_liquidity,
        liquidity_primary_dex=liquidity_primary_dex,
        liquidity_pair_address=liquidity_pair_address,
        wallet_creator=wallet_creator,
        wallet_deployer=wallet_deployer,
        wallet_owner=wallet_owner or owner_address,
        wallet_treasury=wallet_treasury,
        wallet_proxy_admin=admin_address,
        capability_controllers=capability_controllers,
        honeypot_is_suspected=honeypot_is_suspected,
    )


def _enum_value(value: object | None) -> str | None:
    if value is None:
        return None
    return str(getattr(value, "value", value))
