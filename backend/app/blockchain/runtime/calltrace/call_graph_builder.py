"""Runtime call graph builder (M9.2)."""

from __future__ import annotations

from app.blockchain.runtime.calltrace.call_classifier import CallClassifier
from app.blockchain.runtime.calltrace.models import (
    RawTraceNode,
    RuntimeCallGraph,
    RuntimeCallNode,
)


class CallGraphBuilder:
    """Build deterministic runtime call graphs from normalized trace trees."""

    def __init__(self, classifier: CallClassifier | None = None) -> None:
        self._classifier = classifier or CallClassifier()

    def build(self, root: RawTraceNode) -> RuntimeCallGraph:
        nodes: list[RuntimeCallNode] = []
        execution_order: list[str] = []
        order_counter = 0

        def _walk(
            frame: RawTraceNode,
            *,
            node_id: str,
            parent_id: str | None,
            depth: int,
        ) -> None:
            nonlocal order_counter
            selector = frame.input[:4].hex() if len(frame.input) >= 4 else None
            classification = self._classifier.classify(
                frame,
                depth=depth,
                parent_id=parent_id,
            )
            node = RuntimeCallNode(
                node_id=node_id,
                parent_id=parent_id,
                depth=depth,
                order_index=order_counter,
                call_type=frame.call_type,
                classification=classification,
                from_address=frame.from_address.lower(),
                to_address=frame.to_address.lower() if frame.to_address else None,
                value_wei=frame.value_wei,
                gas=frame.gas,
                gas_used=frame.gas_used,
                input=frame.input,
                output=frame.output,
                selector=selector,
                error=frame.error,
                revert_reason=frame.revert_reason,
            )
            nodes.append(node)
            execution_order.append(node_id)
            order_counter += 1

            sorted_children = sorted(
                enumerate(frame.children),
                key=lambda item: (_child_sort_key(item[1]), item[0]),
            )
            for index, child in sorted_children:
                child_id = f"{node_id}.{index}"
                _walk(child, node_id=child_id, parent_id=node_id, depth=depth + 1)

        _walk(root, node_id="0", parent_id=None, depth=0)
        max_depth = max((node.depth for node in nodes), default=0)
        return RuntimeCallGraph(
            root_id="0",
            nodes=tuple(nodes),
            execution_order=tuple(execution_order),
            max_depth=max_depth,
        )


def _child_sort_key(frame: RawTraceNode) -> tuple[str, str, str]:
    return (
        frame.call_type.value,
        (frame.to_address or "").lower(),
        frame.input[:4].hex() if len(frame.input) >= 4 else "",
    )
