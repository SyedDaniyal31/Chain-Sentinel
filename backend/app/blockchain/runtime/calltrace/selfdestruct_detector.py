"""Contract destruction detection (M9.2)."""

from __future__ import annotations

from app.blockchain.runtime.calltrace.models import (
    CallType,
    RuntimeCallGraph,
    RuntimeEvent,
    RuntimeEventType,
)


class SelfdestructDetector:
    """Detect SELFDESTRUCT execution frames."""

    def detect(self, graph: RuntimeCallGraph) -> tuple[RuntimeEvent, ...]:
        events: list[RuntimeEvent] = []
        for node in graph.nodes:
            if node.call_type != CallType.SELFDESTRUCT:
                continue
            events.append(
                RuntimeEvent(
                    event_type=RuntimeEventType.CONTRACT_DESTRUCTION,
                    node_id=node.node_id,
                    description="Contract selfdestruct executed during runtime",
                    metadata={
                        "destroyed_contract": node.from_address,
                        "beneficiary": node.to_address,
                    },
                )
            )
        return tuple(sorted(events, key=lambda item: (item.event_type.value, item.node_id)))
