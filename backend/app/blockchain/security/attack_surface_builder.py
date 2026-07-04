"""Threat surface aggregation builder for M6.4."""

from __future__ import annotations

from app.blockchain.security.attack_path_builder import build_attack_paths
from app.blockchain.security.dependency_analyzer import analyze_external_dependencies
from app.blockchain.security.privilege_analyzer import analyze_privileged_entities
from app.blockchain.security.threat_models import (
    CriticalAsset,
    DependencyGraph,
    DependencyGraphEdge,
    DependencyGraphNode,
    ExternalDependency,
    ThreatSurfaceContext,
    ThreatSurfaceResult,
)
from app.blockchain.security.trust_boundary_detector import detect_trust_boundaries


def build_threat_surface(context: ThreatSurfaceContext) -> ThreatSurfaceResult:
    """Run all M6.4 analyzers and aggregate threat surface output."""
    dependencies = analyze_external_dependencies(context)
    boundaries = detect_trust_boundaries(context)
    privileged = analyze_privileged_entities(context)
    attack_paths = build_attack_paths(context, dependencies, boundaries, privileged)
    critical_assets = build_critical_assets(context, dependencies)
    dependency_graph = build_dependency_graph(context, dependencies)

    return ThreatSurfaceResult(
        external_dependencies=dependencies,
        trust_boundaries=boundaries,
        privileged_entities=privileged,
        attack_paths=attack_paths,
        dependency_graph=dependency_graph,
        critical_assets=critical_assets,
    )


def build_critical_assets(
    context: ThreatSurfaceContext,
    dependencies: list[ExternalDependency],
) -> list[CriticalAsset]:
    """Identify critical assets exposed through external dependencies."""
    assets: dict[str, CriticalAsset] = {}
    contract_id = context.target_address.lower()

    assets[contract_id] = CriticalAsset(
        asset_type="contract",
        label="Target Contract",
        confidence=95,
        address=context.target_address,
    )

    if context.implementation_address:
        assets[context.implementation_address.lower()] = CriticalAsset(
            asset_type="implementation",
            label="Implementation Logic",
            confidence=90,
            address=context.implementation_address,
        )

    if context.liquidity_has_liquidity:
        assets["liquidity_reserves"] = CriticalAsset(
            asset_type="liquidity",
            label="Liquidity Reserves",
            confidence=85,
            address=context.liquidity_pair_address,
        )

    for dep in dependencies:
        if dep.category.value in {"vault", "bridge", "oracle"}:
            key = f"{dep.category.value}:{dep.name.lower()}"
            assets[key] = CriticalAsset(
                asset_type=dep.category.value,
                label=dep.name,
                confidence=dep.confidence,
                address=dep.address,
            )

    if context.wallet_treasury:
        assets[context.wallet_treasury.lower()] = CriticalAsset(
            asset_type="treasury",
            label="Treasury",
            confidence=82,
            address=context.wallet_treasury,
        )

    return sorted(assets.values(), key=lambda item: item.confidence, reverse=True)


def build_dependency_graph(
    context: ThreatSurfaceContext,
    dependencies: list[ExternalDependency],
) -> DependencyGraph:
    """Build a dependency graph for future threat visualization."""
    nodes: dict[str, DependencyGraphNode] = {}
    edges: list[DependencyGraphEdge] = []

    contract_id = f"contract:{context.target_address.lower()}"
    nodes[contract_id] = DependencyGraphNode(
        id=contract_id,
        label="Target Contract",
        node_type="contract",
        address=context.target_address,
    )

    for dep in dependencies:
        node_id = f"{dep.category.value}:{dep.name.lower().replace(' ', '_')}"
        nodes[node_id] = DependencyGraphNode(
            id=node_id,
            label=dep.name if not dep.role else f"{dep.name} ({dep.role})",
            node_type=dep.category.value,
            address=dep.address,
        )
        edges.append(
            DependencyGraphEdge(
                source=contract_id,
                target=node_id,
                relationship="DEPENDS_ON",
                confidence=dep.confidence,
            )
        )

    for relationship in context.relationships:
        target_label = str(relationship.get("target") or "external")
        node_id = f"rel:{target_label.lower().replace(' ', '_')}"
        if node_id not in nodes:
            nodes[node_id] = DependencyGraphNode(
                id=node_id,
                label=target_label,
                node_type="relationship",
            )
        edges.append(
            DependencyGraphEdge(
                source=contract_id,
                target=node_id,
                relationship=str(relationship.get("relationship_type") or "RELATED"),
                confidence=int(relationship.get("confidence") or 70),
            )
        )

    return DependencyGraph(
        nodes=sorted(nodes.values(), key=lambda node: node.id),
        edges=edges,
    )
