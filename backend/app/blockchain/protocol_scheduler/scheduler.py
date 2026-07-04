"""Protocol-wide scan scheduler (M8.3)."""

from __future__ import annotations

import time

from app.blockchain.protocol_graph.models import ProtocolGraph
from app.blockchain.protocol_scheduler.aggregation import aggregate_protocol_evidence
from app.blockchain.protocol_scheduler.dependency_resolver import DependencyResolver
from app.blockchain.protocol_scheduler.executor import NodeScanExecutor, NodeScanWorker
from app.blockchain.protocol_scheduler.metrics import ProtocolScanMetricsCollector
from app.blockchain.protocol_scheduler.models import (
    ExecutionBatch,
    NodeScanResult,
    NodeScanStatus,
    ProtocolScanResult,
    ScanTimingInfo,
    utc_now,
)
from app.blockchain.protocol_scheduler.retry import RetryPolicy
from app.blockchain.protocol_scheduler.worker import LocalAsyncWorkerPool, WorkerPool


class ProtocolScanScheduler:
    """
    Dependency-aware protocol scan orchestrator.

    Consumes a ProtocolGraph, resolves parallel execution batches, and scans
    each node via an injected executor (typically ContractAnalyzer).
    """

    def __init__(
        self,
        executor: NodeScanExecutor,
        *,
        dependency_resolver: DependencyResolver | None = None,
        worker_pool: WorkerPool | None = None,
        retry_policy: RetryPolicy | None = None,
        max_workers: int = 4,
    ) -> None:
        self._executor = executor
        self._dependency_resolver = dependency_resolver or DependencyResolver()
        self._worker_pool = worker_pool or LocalAsyncWorkerPool(max_workers=max_workers)
        self._retry_policy = retry_policy or RetryPolicy()
        self._worker = NodeScanWorker(executor, self._retry_policy)

    async def run(self, graph: ProtocolGraph) -> ProtocolScanResult:
        metrics = ProtocolScanMetricsCollector()
        started_at = utc_now()
        start_perf = time.perf_counter()

        incoming, _ = self._dependency_resolver.build_dependency_maps(graph)
        node_results: dict[str, NodeScanResult] = {
            node.address: NodeScanResult(
                address=node.address,
                status=NodeScanStatus.PENDING,
            )
            for node in graph.nodes
        }

        execution_order: list[str] = []
        execution_batches: list[ExecutionBatch] = []
        batch_index = 0

        while True:
            self._mark_skipped_nodes(node_results, incoming)

            ready = self._ready_nodes(node_results, incoming)
            if not ready:
                self._mark_unresolved_nodes(node_results)
                break

            batch = ExecutionBatch(batch_index, tuple(ready))
            execution_batches.append(batch)
            metrics.record_batch()

            async def _scan(address: str) -> NodeScanResult:
                return await self._worker.scan(address)

            batch_results = await self._worker_pool.run_batch(
                [_scan(address) for address in ready]
            )

            for result in batch_results:
                current = node_results[result.address]
                node_results[result.address] = NodeScanWorker.merge_result(
                    current,
                    result,
                )
                if result.status == NodeScanStatus.COMPLETED:
                    execution_order.append(result.address)
                    metrics.record_node(
                        duration_ms=result.duration_ms,
                        retry_count=result.retry_count,
                    )

            batch_index += 1

        total_duration_ms = (time.perf_counter() - start_perf) * 1000
        completed_at = utc_now()

        ordered_results = tuple(
            node_results[node.address] for node in sorted(graph.nodes, key=lambda item: item.address)
        )
        completed_nodes = tuple(
            address
            for address in execution_order
            if node_results[address].status == NodeScanStatus.COMPLETED
        )
        failed_nodes = tuple(
            result.address
            for result in ordered_results
            if result.status == NodeScanStatus.FAILED
        )

        return ProtocolScanResult(
            execution_order=tuple(execution_order),
            completed_nodes=completed_nodes,
            failed_nodes=failed_nodes,
            aggregated_evidence=aggregate_protocol_evidence(graph, node_results),
            metrics=metrics.build(total_duration_ms),
            timing=ScanTimingInfo(
                started_at=started_at,
                completed_at=completed_at,
                total_duration_ms=total_duration_ms,
            ),
            node_results=ordered_results,
            execution_batches=tuple(execution_batches),
        )

    def resolve_execution_plan(self, graph: ProtocolGraph) -> tuple[ExecutionBatch, ...]:
        """Expose static batch planning for tests and external orchestrators."""
        return self._dependency_resolver.resolve_batches(graph)

    @staticmethod
    def _ready_nodes(
        node_results: dict[str, NodeScanResult],
        incoming: dict[str, tuple[str, ...]],
    ) -> list[str]:
        ready: list[str] = []
        for address, result in node_results.items():
            if result.status != NodeScanStatus.PENDING:
                continue
            dependencies = incoming.get(address, ())
            if dependencies and not all(
                node_results[dependency].status == NodeScanStatus.COMPLETED
                for dependency in dependencies
            ):
                continue
            ready.append(address)
        return sorted(ready)

    @staticmethod
    def _mark_skipped_nodes(
        node_results: dict[str, NodeScanResult],
        incoming: dict[str, tuple[str, ...]],
    ) -> None:
        for address, result in list(node_results.items()):
            if result.status != NodeScanStatus.PENDING:
                continue
            dependencies = incoming.get(address, ())
            if any(
                node_results[dependency].status == NodeScanStatus.FAILED
                for dependency in dependencies
            ):
                node_results[address] = NodeScanWorker.skipped(
                    address,
                    reason="dependency_failed",
                )

    @staticmethod
    def _mark_unresolved_nodes(node_results: dict[str, NodeScanResult]) -> None:
        for address, result in list(node_results.items()):
            if result.status != NodeScanStatus.PENDING:
                continue
            node_results[address] = NodeScanWorker.skipped(
                address,
                reason="unresolved_dependencies",
            )
