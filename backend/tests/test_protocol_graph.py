"""Unit tests for protocol dependency graph builder (M8.2)."""

from __future__ import annotations

import pytest

from app.blockchain.protocol_graph import (
    GraphEdgeType,
    ProtocolGraphBuilder,
    ProtocolGraphTraversal,
    ProtocolGraphValidator,
)
from app.blockchain.protocol_scan.models import (
    ProtocolContract,
    ProtocolDiscoveryResult,
    ProtocolRelationship,
    ProtocolRelationshipType,
    ProtocolRole,
)

PROXY = "0xa231aa3388416ebc1b8f8a51b412327832524ca4"
IMPLEMENTATION = "0xdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef"
ADMIN = "0x1234567890123456789012345678901234567890"
UNISWAP_V2_FACTORY = "0x5c69bee701ef814a2b6a3edd4b1652cb9cc5aa6f"
UNISWAP_V2_ROUTER = "0x7a250d5630b4cf539739df2c5dacb4c659f2488d"
YEARN_VAULT = "0x5f18c75abdae578b483e0628919e8f13bd7f7d0a"
STRATEGY = "0x1111111111111111111111111111111111111112"
WORMHOLE_CORE = "0x98f3c9e6e3f36eaa832f396b124298900b640994"
WORMHOLE_MESSENGER = "0x2222222222222222222222222222222222222222"
ORACLE = "0x3333333333333333333333333333333333333333"
TOKEN = "0x4444444444444444444444444444444444444444"
TREASURY = "0x5555555555555555555555555555555555555555"
POOL = "0x6666666666666666666666666666666666666666"


def _contract(
    address: str,
    role: ProtocolRole,
    *,
    confidence: int = 90,
    metadata: dict | None = None,
) -> ProtocolContract:
    return ProtocolContract(
        address=address.lower(),
        role=role,
        confidence=confidence,
        detection_source="test",
        metadata=metadata or {},
    )


def _relationship(
    source: str,
    target: str,
    relationship_type: ProtocolRelationshipType,
    *,
    confidence: int = 85,
) -> ProtocolRelationship:
    return ProtocolRelationship(
        source_address=source.lower(),
        target_address=target.lower(),
        relationship_type=relationship_type,
        confidence=confidence,
        detection_source="test",
    )


def _discovery(
    root: str,
    *,
    protocol_name: str = "Sample",
    protocol_family: str = "unknown",
    contracts: list[ProtocolContract],
    relationships: list[ProtocolRelationship],
) -> ProtocolDiscoveryResult:
    return ProtocolDiscoveryResult(
        root_address=root.lower(),
        chain_id=1,
        protocol_name=protocol_name,
        protocol_family=protocol_family,
        contracts=tuple(contracts),
        relationships=tuple(relationships),
        confidence=90,
        detection_sources=("test",),
    )


def test_single_node_graph() -> None:
    discovery = _discovery(
        PROXY,
        contracts=[_contract(PROXY, ProtocolRole.ROOT, metadata={"is_root": True})],
        relationships=[],
    )
    graph = ProtocolGraphBuilder().build(discovery)

    assert len(graph.nodes) == 1
    assert graph.root_node == PROXY.lower()
    assert graph.adjacency_map[PROXY.lower()] == ()


def test_proxy_graph_builds_implementation_edge() -> None:
    discovery = _discovery(
        PROXY,
        contracts=[
            _contract(PROXY, ProtocolRole.PROXY, metadata={"implementation_address": IMPLEMENTATION}),
            _contract(IMPLEMENTATION, ProtocolRole.IMPLEMENTATION),
            _contract(ADMIN, ProtocolRole.GOVERNOR),
        ],
        relationships=[
            _relationship(PROXY, IMPLEMENTATION, ProtocolRelationshipType.PROXY_TO_IMPLEMENTATION),
        ],
    )
    graph = ProtocolGraphBuilder().build(discovery)
    edge_types = {edge.relationship_type for edge in graph.edges}
    assert GraphEdgeType.PROXY_TO_IMPLEMENTATION in edge_types


def test_proxy_graph_infers_admin_to_proxy() -> None:
    discovery = _discovery(
        PROXY,
        contracts=[
            _contract(
                PROXY,
                ProtocolRole.PROXY,
                metadata={"admin_address": ADMIN, "implementation_address": IMPLEMENTATION},
            ),
            _contract(IMPLEMENTATION, ProtocolRole.IMPLEMENTATION),
            _contract(ADMIN, ProtocolRole.GOVERNOR),
        ],
        relationships=[
            _relationship(PROXY, IMPLEMENTATION, ProtocolRelationshipType.PROXY_TO_IMPLEMENTATION),
        ],
    )
    graph = ProtocolGraphBuilder().build(discovery)
    assert any(edge.relationship_type == GraphEdgeType.ADMIN_TO_PROXY for edge in graph.edges)


def test_dex_graph_router_to_factory() -> None:
    discovery = _discovery(
        UNISWAP_V2_FACTORY,
        protocol_name="Uniswap V2",
        protocol_family="dex",
        contracts=[
            _contract(
                UNISWAP_V2_FACTORY,
                ProtocolRole.FACTORY,
                metadata={"protocol": "Uniswap V2", "is_root": True},
            ),
            _contract(
                UNISWAP_V2_ROUTER,
                ProtocolRole.ROUTER,
                metadata={"protocol": "Uniswap V2"},
            ),
        ],
        relationships=[
            _relationship(
                UNISWAP_V2_ROUTER,
                UNISWAP_V2_FACTORY,
                ProtocolRelationshipType.ROUTER_TO_FACTORY,
            )
        ],
    )
    graph = ProtocolGraphBuilder().build(discovery)
    traversal = ProtocolGraphTraversal(graph)

    assert traversal.shortest_path(UNISWAP_V2_ROUTER, UNISWAP_V2_FACTORY) == (
        UNISWAP_V2_ROUTER.lower(),
        UNISWAP_V2_FACTORY.lower(),
    )


def test_vault_graph_vault_to_strategy() -> None:
    discovery = _discovery(
        YEARN_VAULT,
        protocol_name="Yearn",
        protocol_family="vault",
        contracts=[
            _contract(YEARN_VAULT, ProtocolRole.VAULT, metadata={"is_root": True}),
            _contract(STRATEGY, ProtocolRole.STRATEGY),
        ],
        relationships=[
            _relationship(YEARN_VAULT, STRATEGY, ProtocolRelationshipType.VAULT_TO_STRATEGY),
        ],
    )
    graph = ProtocolGraphBuilder().build(discovery)
    assert any(edge.relationship_type == GraphEdgeType.VAULT_TO_STRATEGY for edge in graph.edges)


def test_bridge_graph_bridge_to_messenger() -> None:
    discovery = _discovery(
        WORMHOLE_CORE,
        protocol_name="Wormhole",
        protocol_family="bridge",
        contracts=[
            _contract(WORMHOLE_CORE, ProtocolRole.BRIDGE, metadata={"protocol": "Wormhole", "is_root": True}),
            _contract(WORMHOLE_MESSENGER, ProtocolRole.MESSENGER, metadata={"protocol": "Wormhole"}),
        ],
        relationships=[
            _relationship(
                WORMHOLE_CORE,
                WORMHOLE_MESSENGER,
                ProtocolRelationshipType.BRIDGE_TO_MESSENGER,
            )
        ],
    )
    graph = ProtocolGraphBuilder().build(discovery)
    assert any(edge.relationship_type == GraphEdgeType.BRIDGE_TO_MESSENGER for edge in graph.edges)


def test_oracle_to_protocol_edge() -> None:
    discovery = _discovery(
        PROXY,
        contracts=[
            _contract(PROXY, ProtocolRole.ROOT, metadata={"is_root": True}),
            _contract(ORACLE, ProtocolRole.ORACLE),
        ],
        relationships=[],
    )
    graph = ProtocolGraphBuilder().build(discovery)
    assert any(
        edge.relationship_type == GraphEdgeType.ORACLE_TO_PROTOCOL
        and edge.target == PROXY.lower()
        for edge in graph.edges
    )


def test_cycle_detection() -> None:
    a = "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    b = "0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
    c = "0xcccccccccccccccccccccccccccccccccccccccc"
    discovery = _discovery(
        a,
        contracts=[
            _contract(a, ProtocolRole.ROOT, metadata={"is_root": True}),
            _contract(b, ProtocolRole.UNKNOWN),
            _contract(c, ProtocolRole.UNKNOWN),
        ],
        relationships=[
            _relationship(a, b, ProtocolRelationshipType.PROXY_TO_IMPLEMENTATION),
            _relationship(b, c, ProtocolRelationshipType.PROXY_TO_IMPLEMENTATION),
            _relationship(c, a, ProtocolRelationshipType.PROXY_TO_IMPLEMENTATION),
        ],
    )
    graph, report = ProtocolGraphBuilder().build_with_validation(discovery, allow_invalid=True)
    traversal = ProtocolGraphTraversal(graph)
    assert traversal.find_cycles()
    assert report.cycles
    assert traversal.topological_sort() == ()


def test_adjacency_map_contains_outgoing_neighbors() -> None:
    discovery = _discovery(
        UNISWAP_V2_FACTORY,
        contracts=[
            _contract(UNISWAP_V2_FACTORY, ProtocolRole.FACTORY, metadata={"is_root": True}),
            _contract(UNISWAP_V2_ROUTER, ProtocolRole.ROUTER),
        ],
        relationships=[
            _relationship(
                UNISWAP_V2_ROUTER,
                UNISWAP_V2_FACTORY,
                ProtocolRelationshipType.ROUTER_TO_FACTORY,
            )
        ],
    )
    graph = ProtocolGraphBuilder().build(discovery)
    assert UNISWAP_V2_FACTORY.lower() in graph.adjacency_map[UNISWAP_V2_ROUTER.lower()]


def test_graph_traversal_bfs_dfs_and_ancestors() -> None:
    discovery = _discovery(
        UNISWAP_V2_FACTORY,
        contracts=[
            _contract(UNISWAP_V2_FACTORY, ProtocolRole.FACTORY, metadata={"is_root": True}),
            _contract(UNISWAP_V2_ROUTER, ProtocolRole.ROUTER),
            _contract(POOL, ProtocolRole.POOL, metadata={"factory_address": UNISWAP_V2_FACTORY}),
        ],
        relationships=[
            _relationship(
                UNISWAP_V2_ROUTER,
                UNISWAP_V2_FACTORY,
                ProtocolRelationshipType.ROUTER_TO_FACTORY,
            ),
            _relationship(UNISWAP_V2_FACTORY, POOL, ProtocolRelationshipType.FACTORY_TO_POOL),
        ],
    )
    graph = ProtocolGraphBuilder().build(discovery)
    traversal = ProtocolGraphTraversal(graph)

    assert UNISWAP_V2_FACTORY.lower() in traversal.bfs()
    assert UNISWAP_V2_FACTORY.lower() in traversal.dfs()
    assert UNISWAP_V2_ROUTER.lower() in traversal.ancestors(POOL)
    assert POOL.lower() in traversal.descendants(UNISWAP_V2_FACTORY)
    assert traversal.is_dag()


def test_deterministic_ordering() -> None:
    discovery = _discovery(
        UNISWAP_V2_FACTORY,
        protocol_name="Uniswap V2",
        protocol_family="dex",
        contracts=[
            _contract(UNISWAP_V2_FACTORY, ProtocolRole.FACTORY, metadata={"is_root": True}),
            _contract(UNISWAP_V2_ROUTER, ProtocolRole.ROUTER),
        ],
        relationships=[
            _relationship(
                UNISWAP_V2_ROUTER,
                UNISWAP_V2_FACTORY,
                ProtocolRelationshipType.ROUTER_TO_FACTORY,
            )
        ],
    )
    first = ProtocolGraphBuilder().build(discovery)
    second = ProtocolGraphBuilder().build(discovery)
    assert first == second


def test_validation_failure_missing_root() -> None:
    discovery = _discovery(
        PROXY,
        contracts=[_contract(IMPLEMENTATION, ProtocolRole.IMPLEMENTATION)],
        relationships=[],
    )
    graph, report = ProtocolGraphBuilder().build_with_validation(discovery, allow_invalid=True)
    assert not report.is_valid
    assert any(issue.code == "missing_root" for issue in report.issues)
    assert graph.root_node == PROXY.lower()


def test_validation_failure_self_loop() -> None:
    discovery = _discovery(
        PROXY,
        contracts=[_contract(PROXY, ProtocolRole.ROOT, metadata={"is_root": True})],
        relationships=[
            _relationship(PROXY, PROXY, ProtocolRelationshipType.PROXY_TO_IMPLEMENTATION),
        ],
    )
    with pytest.raises(ValueError, match="Invalid protocol graph"):
        ProtocolGraphBuilder().build(discovery)


def test_token_to_treasury_edge() -> None:
    discovery = _discovery(
        TOKEN,
        contracts=[
            _contract(TOKEN, ProtocolRole.TOKEN, metadata={"is_root": True}),
            _contract(TREASURY, ProtocolRole.TREASURY),
        ],
        relationships=[
            _relationship(TOKEN, TREASURY, ProtocolRelationshipType.TOKEN_TO_TREASURY),
        ],
    )
    graph = ProtocolGraphBuilder().build(discovery)
    assert any(edge.relationship_type == GraphEdgeType.TOKEN_TO_TREASURY for edge in graph.edges)


def test_validator_reports_disconnected_nodes() -> None:
    discovery = _discovery(
        PROXY,
        contracts=[
            _contract(PROXY, ProtocolRole.ROOT, metadata={"is_root": True}),
            _contract(IMPLEMENTATION, ProtocolRole.IMPLEMENTATION),
        ],
        relationships=[],
    )
    graph, report = ProtocolGraphBuilder().build_with_validation(discovery, allow_invalid=True)
    assert IMPLEMENTATION.lower() in report.disconnected_nodes
