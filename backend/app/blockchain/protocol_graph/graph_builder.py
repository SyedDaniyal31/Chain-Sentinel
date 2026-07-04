"""Protocol dependency graph builder (M8.2)."""

from __future__ import annotations

from app.blockchain.protocol_graph.edge_builder import ProtocolEdgeBuilder
from app.blockchain.protocol_graph.models import GraphValidationReport, ProtocolEdge, ProtocolGraph, ProtocolNode
from app.blockchain.protocol_graph.node_classifier import ProtocolNodeClassifier, mark_root_node
from app.blockchain.protocol_graph.validator import ProtocolGraphValidator
from app.blockchain.protocol_scan.models import ProtocolDiscoveryResult


class ProtocolGraphBuilder:
    """Build a directed protocol dependency graph from discovery output."""

    def __init__(
        self,
        node_classifier: ProtocolNodeClassifier | None = None,
        edge_builder: ProtocolEdgeBuilder | None = None,
        validator: ProtocolGraphValidator | None = None,
    ) -> None:
        self._node_classifier = node_classifier or ProtocolNodeClassifier()
        self._edge_builder = edge_builder or ProtocolEdgeBuilder()
        self._validator = validator or ProtocolGraphValidator()

    def build(self, discovery: ProtocolDiscoveryResult) -> ProtocolGraph:
        """Construct a validated, deterministically ordered protocol graph."""
        root_address = discovery.root_address.lower()
        nodes = mark_root_node(self._node_classifier.build_nodes(discovery), root_address)
        edges = self._edge_builder.build_edges(discovery)
        adjacency_map = _build_adjacency_map(nodes, edges)

        graph = ProtocolGraph(
            nodes=tuple(nodes),
            edges=tuple(edges),
            root_node=root_address,
            adjacency_map=adjacency_map,
        )
        report = self._validator.validate(graph)
        if not report.is_valid:
            invalid_codes = {issue.code for issue in report.issues}
            raise ValueError(f"Invalid protocol graph: {sorted(invalid_codes)}")
        return graph

    def build_with_validation(
        self,
        discovery: ProtocolDiscoveryResult,
        *,
        allow_invalid: bool = False,
    ) -> tuple[ProtocolGraph, GraphValidationReport]:
        """Build a graph and return the validation report without raising."""
        root_address = discovery.root_address.lower()
        nodes = mark_root_node(self._node_classifier.build_nodes(discovery), root_address)
        edges = self._edge_builder.build_edges(discovery)
        adjacency_map = _build_adjacency_map(nodes, edges)
        graph = ProtocolGraph(
            nodes=tuple(nodes),
            edges=tuple(edges),
            root_node=root_address,
            adjacency_map=adjacency_map,
        )
        report = self._validator.validate(graph)
        if not report.is_valid and not allow_invalid:
            invalid_codes = {issue.code for issue in report.issues}
            raise ValueError(f"Invalid protocol graph: {sorted(invalid_codes)}")
        return graph, report


def _build_adjacency_map(
    nodes: list[ProtocolNode],
    edges: list[ProtocolEdge],
) -> dict[str, tuple[str, ...]]:
    adjacency: dict[str, set[str]] = {node.address: set() for node in nodes}
    for edge in edges:
        adjacency.setdefault(edge.source, set()).add(edge.target)
        adjacency.setdefault(edge.target, set())
    return {address: tuple(sorted(targets)) for address, targets in sorted(adjacency.items())}
