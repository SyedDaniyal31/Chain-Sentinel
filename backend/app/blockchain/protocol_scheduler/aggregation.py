"""Protocol scan result aggregation (M8.3)."""

from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal
from typing import Any

from app.blockchain.protocol_graph.models import ProtocolGraph
from app.blockchain.protocol_scheduler.models import NodeScanResult, NodeScanStatus


def aggregate_protocol_evidence(
    graph: ProtocolGraph,
    node_results: Mapping[str, NodeScanResult],
) -> dict[str, Any]:
    """Merge completed node analyses into protocol-wide evidence."""
    nodes_evidence: dict[str, dict[str, Any]] = {}
    highest_risk_score = Decimal("0.00")
    risk_levels: list[str] = []

    for node in graph.nodes:
        result = node_results.get(node.address)
        if result is None or result.status != NodeScanStatus.COMPLETED:
            continue
        if result.analysis is None:
            continue

        analysis = result.analysis
        if analysis.risk_score > highest_risk_score:
            highest_risk_score = analysis.risk_score
        risk_levels.append(analysis.risk_level.value)

        nodes_evidence[node.address] = {
            "role": node.role.value,
            "protocol_name": node.protocol_name,
            "risk_score": str(analysis.risk_score),
            "risk_level": analysis.risk_level.value,
            "risk_reasons": list(analysis.risk_reasons),
            "is_contract": analysis.is_contract,
            "is_upgradeable": analysis.is_upgradeable,
            "duration_ms": result.duration_ms,
            "retry_count": result.retry_count,
        }

    return {
        "protocol_root": graph.root_node,
        "node_count": len(graph.nodes),
        "completed_count": len(nodes_evidence),
        "failed_count": sum(
            1
            for result in node_results.values()
            if result.status == NodeScanStatus.FAILED
        ),
        "skipped_count": sum(
            1
            for result in node_results.values()
            if result.status == NodeScanStatus.SKIPPED
        ),
        "highest_risk_score": str(highest_risk_score),
        "risk_levels": sorted(set(risk_levels)),
        "nodes": nodes_evidence,
    }
