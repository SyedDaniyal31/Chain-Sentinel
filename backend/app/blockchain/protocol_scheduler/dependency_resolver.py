"""Dependency resolution and execution batch planning (M8.3)."""

from __future__ import annotations

from app.blockchain.protocol_graph.models import ProtocolGraph
from app.blockchain.protocol_scheduler.models import ExecutionBatch


class DependencyResolver:
    """Computes dependency-aware execution batches from a protocol graph."""

    def build_dependency_maps(
        self,
        graph: ProtocolGraph,
    ) -> tuple[dict[str, tuple[str, ...]], dict[str, tuple[str, ...]]]:
        """Return incoming and outgoing adjacency maps keyed by node address."""
        outgoing = graph.adjacency_map
        incoming: dict[str, set[str]] = {node.address: set() for node in graph.nodes}
        for source, targets in outgoing.items():
            for target in targets:
                incoming.setdefault(target, set()).add(source)
        incoming_map = {
            address: tuple(sorted(parents)) for address, parents in incoming.items()
        }
        return incoming_map, outgoing

    def resolve_batches(self, graph: ProtocolGraph) -> tuple[ExecutionBatch, ...]:
        """
        Build parallel execution batches using Kahn topological layering.

        Edges are interpreted as source -> target, meaning the target depends on
        the source completing before it can run.
        """
        incoming, outgoing = self.build_dependency_maps(graph)
        indegree = {
            node.address: len(incoming.get(node.address, ())) for node in graph.nodes
        }
        batches: list[ExecutionBatch] = []
        batch_index = 0

        while True:
            ready = sorted(
                address
                for address, degree in indegree.items()
                if degree == 0
            )
            if not ready:
                break

            batches.append(ExecutionBatch(batch_index, tuple(ready)))
            batch_index += 1

            for address in ready:
                del indegree[address]
                for child in outgoing.get(address, ()):
                    if child not in indegree:
                        continue
                    indegree[child] -= 1

        return tuple(batches)

    def resolve_execution_order(self, graph: ProtocolGraph) -> tuple[str, ...]:
        """Flatten execution batches into a deterministic node order."""
        return tuple(
            address
            for batch in self.resolve_batches(graph)
            for address in batch.addresses
        )
