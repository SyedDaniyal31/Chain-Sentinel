"""Execution gas profiling (M9.2)."""

from __future__ import annotations

from app.blockchain.runtime.calltrace.models import (
    CallClassification,
    GasCallStat,
    GasProfile,
    RuntimeCallGraph,
)


class GasProfiler:
    """Compute gas usage statistics across a runtime call graph."""

    EXTERNAL_GAS_THRESHOLD = 100_000

    def profile(self, graph: RuntimeCallGraph) -> GasProfile:
        stats = tuple(
            GasCallStat(
                node_id=node.node_id,
                call_type=node.call_type,
                to_address=node.to_address,
                selector=node.selector,
                gas_used=node.gas_used,
                depth=node.depth,
            )
            for node in graph.nodes
        )
        total_gas = sum(item.gas_used for item in stats)
        hottest = _top_functions(stats, limit=5)
        deepest_path = _deepest_path(graph)
        expensive_external = tuple(
            sorted(
                (
                    item
                    for item in stats
                    if item.gas_used >= self.EXTERNAL_GAS_THRESHOLD
                    and _is_external(graph, item.node_id)
                ),
                key=lambda item: (-item.gas_used, item.node_id),
            )
        )
        return GasProfile(
            total_gas_used=total_gas,
            call_stats=stats,
            hottest_functions=hottest,
            deepest_path=deepest_path,
            deepest_depth=len(deepest_path) - 1 if deepest_path else 0,
            expensive_external_calls=expensive_external,
        )


def _top_functions(stats: tuple[GasCallStat, ...], *, limit: int) -> tuple[tuple[str, int], ...]:
    totals: dict[str, int] = {}
    for item in stats:
        key = item.selector or item.call_type.value
        totals[key] = totals.get(key, 0) + item.gas_used
    ranked = sorted(totals.items(), key=lambda pair: (-pair[1], pair[0]))
    return tuple(ranked[:limit])


def _deepest_path(graph: RuntimeCallGraph) -> tuple[str, ...]:
    nodes_by_id = {node.node_id: node for node in graph.nodes}
    deepest_node = max(graph.nodes, key=lambda node: (node.depth, node.order_index), default=None)
    if deepest_node is None:
        return ()
    path: list[str] = []
    current_id: str | None = deepest_node.node_id
    while current_id is not None:
        path.append(current_id)
        node = nodes_by_id[current_id]
        current_id = node.parent_id
    return tuple(reversed(path))


def _is_external(graph: RuntimeCallGraph, node_id: str) -> bool:
    for node in graph.nodes:
        if node.node_id != node_id:
            continue
        return node.classification in {
            CallClassification.EXTERNAL,
            CallClassification.TOP_LEVEL,
        }
    return False
