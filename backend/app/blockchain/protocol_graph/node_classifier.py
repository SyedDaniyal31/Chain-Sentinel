"""Protocol graph node classification (M8.2)."""

from __future__ import annotations

from app.blockchain.protocol_graph.models import ProtocolNode
from app.blockchain.protocol_scan.models import ProtocolContract, ProtocolDiscoveryResult, ProtocolRole


class ProtocolNodeClassifier:
    """Convert discovery contracts into graph nodes with enriched metadata."""

    def build_nodes(self, discovery: ProtocolDiscoveryResult) -> list[ProtocolNode]:
        protocol_name = discovery.protocol_name
        nodes: list[ProtocolNode] = []
        for contract in discovery.contracts:
            nodes.append(self.classify_contract(contract, protocol_name, discovery.protocol_family))
        return _dedupe_nodes(nodes)

    @staticmethod
    def classify_contract(
        contract: ProtocolContract,
        protocol_name: str,
        protocol_family: str,
    ) -> ProtocolNode:
        metadata = {
            **contract.metadata,
            "confidence": contract.confidence,
            "detection_source": contract.detection_source,
            "protocol_family": protocol_family,
            "is_root": contract.address == contract.metadata.get("root_address")
            or contract.metadata.get("is_root", False),
        }
        return ProtocolNode(
            address=contract.address,
            role=contract.role,
            protocol_name=protocol_name,
            metadata=metadata,
        )


def _dedupe_nodes(nodes: list[ProtocolNode]) -> list[ProtocolNode]:
    best: dict[str, ProtocolNode] = {}
    for node in nodes:
        existing = best.get(node.address)
        if existing is None:
            best[node.address] = node
            continue
        existing_score = existing.metadata.get("confidence", 0)
        node_score = node.metadata.get("confidence", 0)
        if node_score >= existing_score:
            best[node.address] = node
    return sorted(best.values(), key=lambda item: (item.role.value, item.address))


def mark_root_node(nodes: list[ProtocolNode], root_address: str) -> list[ProtocolNode]:
    """Ensure root metadata is present on the root node."""
    updated: list[ProtocolNode] = []
    for node in nodes:
        if node.address == root_address:
            updated.append(
                ProtocolNode(
                    address=node.address,
                    role=node.role if node.role != ProtocolRole.UNKNOWN else ProtocolRole.ROOT,
                    protocol_name=node.protocol_name,
                    metadata={**node.metadata, "is_root": True, "root_address": root_address},
                )
            )
        else:
            updated.append(
                ProtocolNode(
                    address=node.address,
                    role=node.role,
                    protocol_name=node.protocol_name,
                    metadata={**node.metadata, "root_address": root_address},
                )
            )
    return updated
