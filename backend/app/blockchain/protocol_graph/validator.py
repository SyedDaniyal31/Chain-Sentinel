"""Protocol dependency graph validation (M8.2)."""

from __future__ import annotations

from app.blockchain.protocol_graph.models import (
    GraphValidationIssue,
    GraphValidationReport,
    ProtocolGraph,
)
from app.blockchain.protocol_graph.traversal import ProtocolGraphTraversal


class ProtocolGraphValidator:
    """Validate graph integrity and produce structured reports."""

    def validate(self, graph: ProtocolGraph) -> GraphValidationReport:
        issues: list[GraphValidationIssue] = []
        node_addresses = {node.address for node in graph.nodes}

        if graph.root_node not in node_addresses:
            issues.append(
                GraphValidationIssue(
                    code="missing_root",
                    message="Root node is not present in graph nodes",
                    address=graph.root_node,
                )
            )

        if len(node_addresses) != len(graph.nodes):
            issues.append(
                GraphValidationIssue(
                    code="duplicate_nodes",
                    message="Graph contains duplicate node addresses",
                )
            )

        for edge in graph.edges:
            if edge.source not in node_addresses:
                issues.append(
                    GraphValidationIssue(
                        code="invalid_edge",
                        message=f"Edge source not found in nodes: {edge.source}",
                        address=edge.source,
                    )
                )
            if edge.target not in node_addresses:
                issues.append(
                    GraphValidationIssue(
                        code="invalid_edge",
                        message=f"Edge target not found in nodes: {edge.target}",
                        address=edge.target,
                    )
                )
            if edge.source == edge.target:
                issues.append(
                    GraphValidationIssue(
                        code="self_loop",
                        message=f"Self loop detected on {edge.source}",
                        address=edge.source,
                    )
                )

        traversal = ProtocolGraphTraversal(graph)
        disconnected = tuple(sorted(traversal.disconnected_from_root()))
        cycles = traversal.find_cycles()
        orphan_nodes = tuple(sorted(_find_orphan_nodes(graph)))

        if disconnected:
            issues.append(
                GraphValidationIssue(
                    code="disconnected_nodes",
                    message=f"{len(disconnected)} node(s) disconnected from root",
                )
            )
        if cycles:
            issues.append(
                GraphValidationIssue(
                    code="cycles_detected",
                    message=f"{len(cycles)} cycle(s) detected in graph",
                )
            )
        if orphan_nodes:
            issues.append(
                GraphValidationIssue(
                    code="orphan_nodes",
                    message=f"{len(orphan_nodes)} orphan node(s) with no edges",
                )
            )

        is_valid = not any(
            issue.code
            in {
                "missing_root",
                "duplicate_nodes",
                "invalid_edge",
                "self_loop",
            }
            for issue in issues
        )
        return GraphValidationReport(
            is_valid=is_valid,
            issues=tuple(issues),
            disconnected_nodes=disconnected,
            orphan_nodes=orphan_nodes,
            cycles=cycles,
        )


def _find_orphan_nodes(graph: ProtocolGraph) -> list[str]:
    if len(graph.nodes) <= 1:
        return []
    touched: set[str] = set()
    for edge in graph.edges:
        touched.add(edge.source)
        touched.add(edge.target)
    return [
        node.address
        for node in graph.nodes
        if node.address not in touched and node.address != graph.root_node
    ]
