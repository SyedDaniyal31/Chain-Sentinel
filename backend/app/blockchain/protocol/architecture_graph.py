"""Architecture graph builder for M6.3 cross-protocol intelligence."""

from __future__ import annotations

from app.blockchain.protocol.relationship_models import (
    ArchitectureGraph,
    ArchitectureGraphEdge,
    ArchitectureGraphNode,
    ArchitectureSummary,
    ProtocolRelationship,
    ProtocolRelationshipCandidate,
    RelationshipAnalysisContext,
)


def build_architecture_graph(
    context: RelationshipAnalysisContext,
    candidates: list[ProtocolRelationshipCandidate],
    relationships: list[ProtocolRelationship],
) -> ArchitectureGraph:
    """Build a visualization-ready graph from relationship candidates and normalized edges."""
    nodes: dict[str, ArchitectureGraphNode] = {}
    contract_id = f"contract:{context.target_address.lower()}"

    nodes[contract_id] = ArchitectureGraphNode(
        id=contract_id,
        label="Target Contract",
        node_type="contract",
        address=context.target_address,
    )

    for candidate in candidates:
        _upsert_node(
            nodes,
            ArchitectureGraphNode(
                id=candidate.target_id,
                label=candidate.target_label,
                node_type=candidate.target_type.value,
                address=candidate.target_address,
            ),
        )
        _upsert_node(
            nodes,
            ArchitectureGraphNode(
                id=candidate.source_id,
                label=candidate.source_label,
                node_type=candidate.source_type.value,
                address=context.target_address if candidate.source_type.value == "contract" else None,
            ),
        )

    edges = [
        ArchitectureGraphEdge(
            source=_resolve_node_id(relationship.source, nodes, contract_id),
            target=_resolve_node_id(relationship.target, nodes, contract_id),
            relationship=relationship.relationship_type.value,
            confidence=relationship.confidence,
            detection_source=relationship.detection_source,
        )
        for relationship in relationships
    ]

    return ArchitectureGraph(nodes=sorted(nodes.values(), key=lambda node: node.id), edges=edges)


def build_architecture_summary(
    context: RelationshipAnalysisContext,
    relationships: list[ProtocolRelationship],
) -> ArchitectureSummary:
    """Generate a data-driven architecture summary from detector outputs."""
    stack: list[str] = []
    if context.standards:
        stack.extend(context.standards)
    if context.protocol_family not in {"unknown"}:
        stack.append(context.protocol_family)
    for category, items in (
        ("dex", context.dexes),
        ("lending", context.lending),
        ("oracle", context.oracles),
        ("bridge", context.bridges),
        ("vault", context.vaults),
    ):
        for item in items:
            name = str(item.get("name") or item.get("standard") or category)
            stack.append(name)

    oracle = _first_name(context.oracles)
    liquidity = context.liquidity_primary_dex
    bridge = _first_name(context.bridges)
    governance = _first_governance_label(context, relationships)
    upgradeability = _upgradeability_label(context)
    ownership = _ownership_label(context)

    application_type = _application_type(context)

    return ArchitectureSummary(
        application_type=application_type,
        protocol_stack=_dedupe(stack),
        oracle=oracle,
        liquidity=liquidity,
        bridge=bridge,
        governance=governance,
        upgradeability=upgradeability,
        ownership=ownership,
    )


def _upsert_node(nodes: dict[str, ArchitectureGraphNode], node: ArchitectureGraphNode) -> None:
    existing = nodes.get(node.id)
    if existing is None:
        nodes[node.id] = node


def _resolve_node_id(label: str, nodes: dict[str, ArchitectureGraphNode], default_id: str) -> str:
    for node in nodes.values():
        if node.label == label:
            return node.id
    return default_id


def _first_name(items: list[dict]) -> str | None:
    if not items:
        return None
    return str(items[0].get("name") or items[0].get("standard"))


def _first_governance_label(
    context: RelationshipAnalysisContext,
    relationships: list[ProtocolRelationship],
) -> str | None:
    if context.governance_protocols:
        return str(context.governance_protocols[0].get("name"))
    for relationship in relationships:
        if relationship.relationship_type.value == "GOVERNED_BY":
            return relationship.target
    if context.governance_type and context.governance_type not in {"none", "unknown"}:
        return context.governance_type
    return None


def _upgradeability_label(context: RelationshipAnalysisContext) -> str | None:
    if context.is_upgradeable:
        if context.proxy_type not in {"none", "unknown"}:
            return context.proxy_type
        return "upgradeable_proxy"
    if context.upgrade_authority and context.upgrade_authority not in {"none", "unknown"}:
        return context.upgrade_authority
    return "non_upgradeable"


def _ownership_label(context: RelationshipAnalysisContext) -> str | None:
    if context.governance_ownership_renounced:
        return "renounced"
    if context.wallet_owner:
        return context.wallet_owner
    if context.governance_ownership_address:
        return context.governance_ownership_address
    if context.wallet_deployer:
        return context.wallet_deployer
    return None


def _application_type(context: RelationshipAnalysisContext) -> str:
    family = context.protocol_family
    if family not in {"unknown"}:
        return family
    if context.standards:
        return context.standards[0].lower()
    if context.liquidity_has_liquidity:
        return "token"
    return "unknown"


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        key = value.lower()
        if key in seen:
            continue
        seen.add(key)
        ordered.append(value)
    return ordered
