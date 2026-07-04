"""Architecture graph unit tests (M6.3)."""

from app.blockchain.protocol.architecture_graph import build_architecture_graph, build_architecture_summary
from app.blockchain.protocol.relationship_engine import normalize_relationships
from app.blockchain.protocol.relationship_builder import build_relationship_candidates
from app.blockchain.protocol.relationship_models import RelationshipAnalysisContext, RelationshipType


def test_build_architecture_graph_contains_contract_node_and_edges() -> None:
    context = RelationshipAnalysisContext(
        target_address="0x742d35cc6634c0532925a3b844bc9e7595f0beb0",
        protocol_family="bridge",
        dexes=[{"name": "Uniswap V3", "role": "pool", "confidence": 90}],
        bridges=[{"name": "LayerZero", "role": "endpoint", "confidence": 94}],
    )
    candidates = build_relationship_candidates(context)
    relationships = normalize_relationships(candidates)
    graph = build_architecture_graph(context, candidates, relationships)

    assert any(node.node_type == "contract" for node in graph.nodes)
    assert len(graph.edges) == len(relationships)
    assert all(edge.relationship in {item.value for item in RelationshipType} for edge in graph.edges)


def test_build_architecture_summary_is_data_driven() -> None:
    context = RelationshipAnalysisContext(
        target_address="0x742d35cc6634c0532925a3b844bc9e7595f0beb0",
        protocol_family="vault",
        standards=["ERC4626"],
        oracles=[{"name": "Chainlink", "confidence": 90}],
        bridges=[{"name": "LayerZero", "role": "endpoint", "confidence": 92}],
        liquidity_has_liquidity=True,
        liquidity_primary_dex="uniswap",
        governance_protocols=[{"name": "Governor Bravo", "confidence": 90}],
        is_upgradeable=True,
        proxy_type="transparent",
        wallet_owner="0x1234567890123456789012345678901234567890",
    )
    candidates = build_relationship_candidates(context)
    relationships = normalize_relationships(candidates)
    summary = build_architecture_summary(context, relationships)

    assert summary.application_type == "vault"
    assert "ERC4626" in summary.protocol_stack
    assert summary.oracle == "Chainlink"
    assert summary.liquidity == "uniswap"
    assert summary.bridge == "LayerZero"
    assert summary.upgradeability == "transparent"
    assert summary.ownership == "0x1234567890123456789012345678901234567890"
