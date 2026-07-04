"""Protocol graph edge construction (M8.2)."""

from __future__ import annotations

from app.blockchain.protocol_graph.models import GraphEdgeType, ProtocolEdge
from app.blockchain.protocol_scan.models import (
    ProtocolDiscoveryResult,
    ProtocolRelationship,
    ProtocolRelationshipType,
    ProtocolRole,
)

_DISCOVERY_EDGE_MAP: dict[ProtocolRelationshipType, GraphEdgeType] = {
    ProtocolRelationshipType.PROXY_TO_IMPLEMENTATION: GraphEdgeType.PROXY_TO_IMPLEMENTATION,
    ProtocolRelationshipType.GOVERNOR_TO_TIMELOCK: GraphEdgeType.GOVERNOR_TO_TIMELOCK,
    ProtocolRelationshipType.ROUTER_TO_FACTORY: GraphEdgeType.ROUTER_TO_FACTORY,
    ProtocolRelationshipType.FACTORY_TO_POOL: GraphEdgeType.FACTORY_TO_POOL,
    ProtocolRelationshipType.VAULT_TO_STRATEGY: GraphEdgeType.VAULT_TO_STRATEGY,
    ProtocolRelationshipType.TOKEN_TO_TREASURY: GraphEdgeType.TOKEN_TO_TREASURY,
    ProtocolRelationshipType.BRIDGE_TO_MESSENGER: GraphEdgeType.BRIDGE_TO_MESSENGER,
}


class ProtocolEdgeBuilder:
    """Build typed graph edges from discovery relationships and inferred links."""

    def build_edges(self, discovery: ProtocolDiscoveryResult) -> list[ProtocolEdge]:
        edges: list[ProtocolEdge] = []
        known_addresses = {contract.address for contract in discovery.contracts}

        for relationship in discovery.relationships:
            edge = self.from_relationship(relationship)
            if edge.source in known_addresses and edge.target in known_addresses:
                edges.append(edge)

        edges.extend(self._infer_admin_to_proxy(discovery))
        edges.extend(self._infer_oracle_to_protocol(discovery))
        edges.extend(self._infer_depends_on(discovery, known_addresses))

        return _dedupe_edges(edges)

    @staticmethod
    def from_relationship(relationship: ProtocolRelationship) -> ProtocolEdge:
        edge_type = _DISCOVERY_EDGE_MAP.get(
            relationship.relationship_type,
            GraphEdgeType.DEPENDS_ON,
        )
        return ProtocolEdge(
            source=relationship.source_address,
            target=relationship.target_address,
            relationship_type=edge_type,
            confidence=relationship.confidence,
        )

    @staticmethod
    def _infer_admin_to_proxy(discovery: ProtocolDiscoveryResult) -> list[ProtocolEdge]:
        edges: list[ProtocolEdge] = []
        contracts_by_address = {contract.address: contract for contract in discovery.contracts}

        for contract in discovery.contracts:
            if contract.role not in {ProtocolRole.PROXY, ProtocolRole.ROOT}:
                continue
            admin_address = contract.metadata.get("admin_address")
            if not isinstance(admin_address, str):
                continue
            admin_address = admin_address.lower()
            if admin_address not in contracts_by_address:
                continue
            edges.append(
                ProtocolEdge(
                    source=admin_address,
                    target=contract.address,
                    relationship_type=GraphEdgeType.ADMIN_TO_PROXY,
                    confidence=min(
                        contract.confidence,
                        contracts_by_address[admin_address].confidence,
                    ),
                )
            )
        return edges

    @staticmethod
    def _infer_oracle_to_protocol(discovery: ProtocolDiscoveryResult) -> list[ProtocolEdge]:
        edges: list[ProtocolEdge] = []
        root = discovery.root_address.lower()
        for contract in discovery.contracts:
            if contract.role != ProtocolRole.ORACLE:
                continue
            edges.append(
                ProtocolEdge(
                    source=contract.address,
                    target=root,
                    relationship_type=GraphEdgeType.ORACLE_TO_PROTOCOL,
                    confidence=contract.confidence,
                )
            )
        return edges

    @staticmethod
    def _infer_depends_on(
        discovery: ProtocolDiscoveryResult,
        known_addresses: set[str],
    ) -> list[ProtocolEdge]:
        edges: list[ProtocolEdge] = []
        existing_pairs = {
            (relationship.source_address, relationship.target_address)
            for relationship in discovery.relationships
        }
        root = discovery.root_address.lower()

        for contract in discovery.contracts:
            if contract.address == root:
                continue
            dependency_target = contract.metadata.get("depends_on")
            if isinstance(dependency_target, str):
                target = dependency_target.lower()
                if target in known_addresses and (contract.address, target) not in existing_pairs:
                    edges.append(
                        ProtocolEdge(
                            source=contract.address,
                            target=target,
                            relationship_type=GraphEdgeType.DEPENDS_ON,
                            confidence=contract.confidence,
                        )
                    )
        return edges


def _dedupe_edges(edges: list[ProtocolEdge]) -> list[ProtocolEdge]:
    best: dict[tuple[str, str, str], ProtocolEdge] = {}
    for edge in edges:
        key = (edge.source, edge.target, edge.relationship_type.value)
        existing = best.get(key)
        if existing is None or edge.confidence > existing.confidence:
            best[key] = edge
    return sorted(
        best.values(),
        key=lambda item: (item.relationship_type.value, item.source, item.target),
    )
