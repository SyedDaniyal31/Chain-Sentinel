"""Contract creation detection (M9.2)."""

from __future__ import annotations

from app.blockchain.runtime.calltrace.models import (
    CallType,
    RuntimeCallGraph,
    RuntimeEvent,
    RuntimeEventType,
)


class CreateDetector:
    """Detect CREATE and CREATE2 deployment frames."""

    def detect(self, graph: RuntimeCallGraph) -> tuple[RuntimeEvent, ...]:
        events: list[RuntimeEvent] = []
        for node in graph.nodes:
            if node.call_type not in {CallType.CREATE, CallType.CREATE2}:
                continue
            events.append(
                RuntimeEvent(
                    event_type=RuntimeEventType.CONTRACT_CREATION,
                    node_id=node.node_id,
                    description=f"{node.call_type.value} contract deployment detected",
                    metadata={
                        "creation_type": node.call_type.value,
                        "deployer": node.from_address,
                        "created_address": node.to_address,
                    },
                )
            )
        return tuple(sorted(events, key=lambda item: (item.event_type.value, item.node_id)))
