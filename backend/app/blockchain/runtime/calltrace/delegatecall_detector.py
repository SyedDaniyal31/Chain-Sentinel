"""Delegatecall and proxy execution detection (M9.2)."""

from __future__ import annotations

from app.blockchain.runtime.calltrace.models import (
    CallType,
    RuntimeCallGraph,
    RuntimeCallNode,
    RuntimeEvent,
    RuntimeEventType,
)


class DelegatecallDetector:
    """Detect delegatecall chains and proxy execution patterns."""

    def detect(self, graph: RuntimeCallGraph) -> tuple[RuntimeEvent, ...]:
        events: list[RuntimeEvent] = []
        nodes_by_id = {node.node_id: node for node in graph.nodes}

        delegate_nodes = [node for node in graph.nodes if node.call_type == CallType.DELEGATECALL]
        if len(delegate_nodes) >= 2:
            events.append(
                RuntimeEvent(
                    event_type=RuntimeEventType.DELEGATECALL_CHAIN,
                    node_id=delegate_nodes[0].node_id,
                    description="Delegatecall chain detected across multiple execution frames",
                    metadata={
                        "delegatecall_count": len(delegate_nodes),
                        "node_ids": [node.node_id for node in delegate_nodes],
                    },
                )
            )

        for node in delegate_nodes:
            parent = nodes_by_id.get(node.parent_id or "")
            if parent and parent.to_address and node.to_address and parent.to_address != node.to_address:
                events.append(
                    RuntimeEvent(
                        event_type=RuntimeEventType.PROXY_EXECUTION,
                        node_id=node.node_id,
                        description="Proxy contract delegated execution to implementation logic",
                        metadata={
                            "proxy_address": parent.to_address,
                            "implementation_address": node.to_address,
                        },
                    )
                )

        return tuple(sorted(events, key=_event_sort_key))


def _event_sort_key(event: RuntimeEvent) -> tuple[str, str]:
    return (event.event_type.value, event.node_id)
