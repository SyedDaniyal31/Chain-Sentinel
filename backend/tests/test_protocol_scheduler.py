"""Unit tests for parallel protocol scan scheduler (M8.3)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.blockchain.protocol_graph.models import GraphEdgeType, ProtocolEdge, ProtocolGraph, ProtocolNode
from app.blockchain.protocol_scan.models import ProtocolRole
from app.blockchain.protocol_scheduler import (
    DependencyResolver,
    ExecutionBatch,
    NodeScanStatus,
    ProtocolScanScheduler,
    RetryPolicy,
)
from app.models.enums import RiskLevel
from app.schemas.scan_result import ContractAnalysisData

NODE_A = "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
NODE_B = "0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
NODE_C = "0xcccccccccccccccccccccccccccccccccccccccc"
NODE_D = "0xdddddddddddddddddddddddddddddddddddddddd"
NODE_E = "0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee"


def _analysis(address: str, *, risk_score: str = "10.00") -> ContractAnalysisData:
    return ContractAnalysisData(
        chain_id=1,
        latest_block=100,
        is_contract=True,
        bytecode_size=128,
        is_upgradeable=False,
        implementation_address=None,
        admin_address=None,
        admin_type=None,
        owner_address=None,
        owner_type=None,
        is_timelock=False,
        min_delay=None,
        mint_capability=False,
        pause_capability=False,
        blacklist_capability=False,
        ownership_capability=False,
        trading_enabled_control=False,
        whitelist_control=False,
        blacklist_sell_blocking=False,
        transfer_tax_control=False,
        can_buy=None,
        can_sell=None,
        buy_tax_bps=None,
        sell_tax_bps=None,
        trade_simulated=False,
        risk_score=Decimal(risk_score),
        risk_level=RiskLevel.LOW,
        risk_reasons=[f"scan:{address}"],
    )


def _node(address: str, *, role: ProtocolRole = ProtocolRole.UNKNOWN) -> ProtocolNode:
    return ProtocolNode(
        address=address.lower(),
        role=role,
        protocol_name="test-protocol",
    )


def _edge(source: str, target: str) -> ProtocolEdge:
    return ProtocolEdge(
        source=source.lower(),
        target=target.lower(),
        relationship_type=GraphEdgeType.DEPENDS_ON,
        confidence=90,
    )


def _build_graph(
    *,
    root: str,
    edges: list[tuple[str, str]],
    extra_nodes: list[str] | None = None,
) -> ProtocolGraph:
    addresses = {root.lower()}
    for source, target in edges:
        addresses.add(source.lower())
        addresses.add(target.lower())
    if extra_nodes:
        addresses.update(node.lower() for node in extra_nodes)

    nodes = tuple(
        _node(address, role=ProtocolRole.ROOT if address == root.lower() else ProtocolRole.UNKNOWN)
        for address in sorted(addresses)
    )
    graph_edges = tuple(_edge(source, target) for source, target in edges)

    adjacency: dict[str, list[str]] = {node.address: [] for node in nodes}
    for edge in graph_edges:
        adjacency[edge.source].append(edge.target)
    adjacency_map = {address: tuple(sorted(children)) for address, children in adjacency.items()}

    return ProtocolGraph(
        nodes=nodes,
        edges=graph_edges,
        root_node=root.lower(),
        adjacency_map=adjacency_map,
    )


class MockNodeScanExecutor:
    """Configurable executor for scheduler tests."""

    def __init__(
        self,
        *,
        fail_addresses: set[str] | None = None,
        fail_attempts: dict[str, int] | None = None,
        risk_scores: dict[str, str] | None = None,
    ) -> None:
        self.fail_addresses = {address.lower() for address in (fail_addresses or set())}
        self.fail_attempts = {
            address.lower(): count for address, count in (fail_attempts or {}).items()
        }
        self.risk_scores = {
            address.lower(): score for address, score in (risk_scores or {}).items()
        }
        self.calls: list[str] = []
        self.attempt_counts: dict[str, int] = {}

    async def analyze_node(self, address: str) -> ContractAnalysisData:
        normalized = address.lower()
        self.calls.append(normalized)
        self.attempt_counts[normalized] = self.attempt_counts.get(normalized, 0) + 1

        if normalized in self.fail_addresses:
            raise RuntimeError(f"scan failed for {normalized}")

        required_failures = self.fail_attempts.get(normalized, 0)
        if self.attempt_counts[normalized] <= required_failures:
            raise RuntimeError(f"temporary failure for {normalized}")

        score = self.risk_scores.get(normalized, "10.00")
        return _analysis(normalized, risk_score=score)


def test_dependency_resolver_linear_chain() -> None:
    graph = _build_graph(root=NODE_A, edges=[(NODE_A, NODE_B), (NODE_B, NODE_C)])
    resolver = DependencyResolver()

    batches = resolver.resolve_batches(graph)
    assert batches == (
        ExecutionBatch(0, (NODE_A.lower(),)),
        ExecutionBatch(1, (NODE_B.lower(),)),
        ExecutionBatch(2, (NODE_C.lower(),)),
    )
    assert resolver.resolve_execution_order(graph) == (
        NODE_A.lower(),
        NODE_B.lower(),
        NODE_C.lower(),
    )


def test_dependency_resolver_parallel_branches() -> None:
    graph = _build_graph(
        root=NODE_A,
        edges=[(NODE_A, NODE_B), (NODE_A, NODE_C)],
    )
    resolver = DependencyResolver()

    batches = resolver.resolve_batches(graph)
    assert batches[0].addresses == (NODE_A.lower(),)
    assert batches[1].addresses == (NODE_B.lower(), NODE_C.lower())
    assert resolver.resolve_execution_order(graph) == (
        NODE_A.lower(),
        NODE_B.lower(),
        NODE_C.lower(),
    )


@pytest.mark.asyncio
async def test_scheduler_executes_linear_chain_in_order() -> None:
    graph = _build_graph(root=NODE_A, edges=[(NODE_A, NODE_B), (NODE_B, NODE_C)])
    executor = MockNodeScanExecutor()
    scheduler = ProtocolScanScheduler(executor)

    result = await scheduler.run(graph)

    assert result.execution_order == (
        NODE_A.lower(),
        NODE_B.lower(),
        NODE_C.lower(),
    )
    assert result.completed_nodes == result.execution_order
    assert result.failed_nodes == ()
    assert len(result.execution_batches) == 3
    assert executor.calls == list(result.execution_order)


@pytest.mark.asyncio
async def test_scheduler_executes_parallel_branches() -> None:
    graph = _build_graph(
        root=NODE_A,
        edges=[(NODE_A, NODE_B), (NODE_A, NODE_C), (NODE_B, NODE_D), (NODE_C, NODE_D)],
    )
    executor = MockNodeScanExecutor()
    scheduler = ProtocolScanScheduler(executor, max_workers=2)

    result = await scheduler.run(graph)

    assert result.execution_batches[1].addresses == (NODE_B.lower(), NODE_C.lower())
    assert set(result.execution_order[:3]) == {NODE_A.lower(), NODE_B.lower(), NODE_C.lower()}
    assert result.execution_order[-1] == NODE_D.lower()
    assert result.metrics.parallel_batches_executed == 3
    assert result.metrics.nodes_scanned == 4


@pytest.mark.asyncio
async def test_scheduler_retry_behavior() -> None:
    graph = _build_graph(root=NODE_A, edges=[])
    executor = MockNodeScanExecutor(fail_attempts={NODE_A: 2})
    scheduler = ProtocolScanScheduler(
        executor,
        retry_policy=RetryPolicy(max_attempts=3),
    )

    result = await scheduler.run(graph)

    assert result.completed_nodes == (NODE_A.lower(),)
    assert executor.attempt_counts[NODE_A.lower()] == 3
    assert result.metrics.retry_count == 2
    assert result.node_results[0].retry_count == 2


@pytest.mark.asyncio
async def test_scheduler_failure_isolation() -> None:
    graph = _build_graph(
        root=NODE_A,
        edges=[(NODE_A, NODE_B), (NODE_B, NODE_C), (NODE_A, NODE_D)],
    )
    executor = MockNodeScanExecutor(fail_addresses={NODE_B})
    scheduler = ProtocolScanScheduler(executor, retry_policy=RetryPolicy(max_attempts=1))

    result = await scheduler.run(graph)

    statuses = {item.address: item.status for item in result.node_results}
    assert statuses[NODE_A.lower()] == NodeScanStatus.COMPLETED
    assert statuses[NODE_B.lower()] == NodeScanStatus.FAILED
    assert statuses[NODE_C.lower()] == NodeScanStatus.SKIPPED
    assert statuses[NODE_D.lower()] == NodeScanStatus.COMPLETED
    assert result.failed_nodes == (NODE_B.lower(),)
    assert NODE_C.lower() not in result.completed_nodes
    assert NODE_D.lower() in result.completed_nodes


@pytest.mark.asyncio
async def test_scheduler_deterministic_ordering_for_equivalent_graphs() -> None:
    graph = _build_graph(
        root=NODE_A,
        edges=[(NODE_A, NODE_B), (NODE_A, NODE_C)],
    )
    executor_one = MockNodeScanExecutor()
    executor_two = MockNodeScanExecutor()

    result_one = await ProtocolScanScheduler(executor_one).run(graph)
    result_two = await ProtocolScanScheduler(executor_two).run(graph)

    assert result_one.execution_order == result_two.execution_order
    assert result_one.execution_batches == result_two.execution_batches
    assert result_one.execution_order == (
        NODE_A.lower(),
        NODE_B.lower(),
        NODE_C.lower(),
    )


@pytest.mark.asyncio
async def test_scheduler_aggregation_correctness() -> None:
    graph = _build_graph(
        root=NODE_A,
        edges=[(NODE_A, NODE_B)],
        extra_nodes=[NODE_C],
    )
    executor = MockNodeScanExecutor(
        risk_scores={
            NODE_A: "5.00",
            NODE_B: "25.00",
            NODE_C: "15.00",
        }
    )
    scheduler = ProtocolScanScheduler(executor)

    result = await scheduler.run(graph)

    evidence = result.aggregated_evidence
    assert evidence["protocol_root"] == NODE_A.lower()
    assert evidence["node_count"] == 3
    assert evidence["completed_count"] == 3
    assert evidence["highest_risk_score"] == "25.00"
    assert set(evidence["nodes"]) == {
        NODE_A.lower(),
        NODE_B.lower(),
        NODE_C.lower(),
    }
    assert evidence["nodes"][NODE_B.lower()]["risk_score"] == "25.00"


@pytest.mark.asyncio
async def test_scheduler_metrics_reporting() -> None:
    graph = _build_graph(
        root=NODE_A,
        edges=[(NODE_A, NODE_B), (NODE_A, NODE_C)],
    )
    executor = MockNodeScanExecutor()
    scheduler = ProtocolScanScheduler(executor)

    result = await scheduler.run(graph)

    assert result.metrics.nodes_scanned == 3
    assert result.metrics.parallel_batches_executed == 2
    assert result.metrics.total_duration_ms >= 0
    assert result.metrics.average_node_duration_ms >= 0
    assert result.timing.total_duration_ms == result.metrics.total_duration_ms


@pytest.mark.asyncio
async def test_scheduler_exposes_static_execution_plan() -> None:
    graph = _build_graph(root=NODE_A, edges=[(NODE_A, NODE_B), (NODE_B, NODE_C)])
    scheduler = ProtocolScanScheduler(MockNodeScanExecutor())

    plan = scheduler.resolve_execution_plan(graph)
    assert [batch.addresses for batch in plan] == [
        (NODE_A.lower(),),
        (NODE_B.lower(),),
        (NODE_C.lower(),),
    ]


@pytest.mark.asyncio
async def test_scheduler_marks_exhausted_retries_as_failed() -> None:
    graph = _build_graph(root=NODE_A, edges=[])
    executor = MockNodeScanExecutor(fail_addresses={NODE_A})
    scheduler = ProtocolScanScheduler(
        executor,
        retry_policy=RetryPolicy(max_attempts=2),
    )

    result = await scheduler.run(graph)

    assert result.failed_nodes == (NODE_A.lower(),)
    assert result.metrics.nodes_scanned == 0
    assert result.metrics.retry_count == 0
    assert executor.attempt_counts[NODE_A.lower()] == 2
