"""Dependency graph unit tests (M6.4)."""

from app.blockchain.security.attack_surface_builder import build_dependency_graph
from app.blockchain.security.dependency_analyzer import analyze_external_dependencies
from app.blockchain.security.threat_models import ThreatSurfaceContext


def test_build_dependency_graph_links_contract_to_dependencies() -> None:
    context = ThreatSurfaceContext(
        target_address="0x742d35cc6634c0532925a3b844bc9e7595f0beb0",
        bridges=[{"name": "LayerZero", "role": "endpoint", "confidence": 94}],
        oracles=[{"name": "Chainlink", "confidence": 88}],
        relationships=[
            {
                "source": "Target Contract",
                "target": "Chainlink",
                "relationship_type": "PRICES_WITH",
                "confidence": 88,
                "detection_source": "protocol_intelligence.oracle",
            }
        ],
    )
    dependencies = analyze_external_dependencies(context)
    graph = build_dependency_graph(context, dependencies)
    assert any(node.node_type == "contract" for node in graph.nodes)
    assert graph.edges
    assert all(edge.relationship for edge in graph.edges)
