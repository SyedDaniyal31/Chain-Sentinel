"""Aggregate runtime execution event detection (M9.2)."""

from __future__ import annotations

from app.blockchain.runtime.calltrace.create_detector import CreateDetector
from app.blockchain.runtime.calltrace.delegatecall_detector import DelegatecallDetector
from app.blockchain.runtime.calltrace.models import (
    CallClassification,
    CallType,
    RuntimeCallGraph,
    RuntimeEvent,
    RuntimeEventType,
)
from app.blockchain.runtime.calltrace.selfdestruct_detector import SelfdestructDetector

FLASH_LOAN_SELECTORS = {
    "5cffe9de",  # flashLoan / sendMessage variants in aggregators
    "ab9c4b5d",  # flashLoan(address,uint256,bytes)
    "42b0b77c",  # flashLoan(address,address,uint256,bytes)
}


class RuntimeEventAnalyzer:
    """Detect recursive calls, flash-loan callbacks, and unexpected external calls."""

    def __init__(
        self,
        delegatecall_detector: DelegatecallDetector | None = None,
        create_detector: CreateDetector | None = None,
        selfdestruct_detector: SelfdestructDetector | None = None,
    ) -> None:
        self._delegatecall_detector = delegatecall_detector or DelegatecallDetector()
        self._create_detector = create_detector or CreateDetector()
        self._selfdestruct_detector = selfdestruct_detector or SelfdestructDetector()

    def analyze(
        self,
        graph: RuntimeCallGraph,
        *,
        trusted_addresses: set[str] | None = None,
    ) -> tuple[RuntimeEvent, ...]:
        trusted = {address.lower() for address in (trusted_addresses or set())}
        events: list[RuntimeEvent] = []
        events.extend(self._delegatecall_detector.detect(graph))
        events.extend(self._create_detector.detect(graph))
        events.extend(self._selfdestruct_detector.detect(graph))
        events.extend(_detect_recursive_calls(graph))
        events.extend(_detect_flash_loan_callbacks(graph))
        events.extend(_detect_unexpected_external_calls(graph, trusted))
        return _dedupe_events(events)


def _detect_recursive_calls(graph: RuntimeCallGraph) -> list[RuntimeEvent]:
    events: list[RuntimeEvent] = []
    seen_pairs: set[tuple[str, str, str]] = set()
    for node in graph.nodes:
        if not node.to_address:
            continue
        key = (node.from_address, node.to_address, node.selector or "")
        if key in seen_pairs:
            events.append(
                RuntimeEvent(
                    event_type=RuntimeEventType.RECURSIVE_CALL,
                    node_id=node.node_id,
                    description="Recursive call pattern detected between the same caller and callee",
                    metadata={
                        "from_address": node.from_address,
                        "to_address": node.to_address,
                        "selector": node.selector,
                        "depth": node.depth,
                    },
                )
            )
        seen_pairs.add(key)
    return events


def _detect_flash_loan_callbacks(graph: RuntimeCallGraph) -> list[RuntimeEvent]:
    events: list[RuntimeEvent] = []
    flash_nodes = [
        node
        for node in graph.nodes
        if node.selector in FLASH_LOAN_SELECTORS or _looks_like_flash_loan(node)
    ]
    for flash_node in flash_nodes:
        callback_nodes = [
            child
            for child in graph.nodes
            if child.parent_id == flash_node.node_id and child.depth == flash_node.depth + 1
        ]
        if callback_nodes:
            events.append(
                RuntimeEvent(
                    event_type=RuntimeEventType.FLASH_LOAN_CALLBACK,
                    node_id=flash_node.node_id,
                    description="Flash-loan style borrow with nested callback execution detected",
                    metadata={
                        "borrow_node": flash_node.node_id,
                        "callback_nodes": [node.node_id for node in callback_nodes],
                    },
                )
            )
    return events


def _detect_unexpected_external_calls(
    graph: RuntimeCallGraph,
    trusted_addresses: set[str],
) -> list[RuntimeEvent]:
    events: list[RuntimeEvent] = []
    root_to = graph.nodes[0].to_address if graph.nodes else None
    for node in graph.nodes:
        if node.classification not in {CallClassification.EXTERNAL, CallClassification.TOP_LEVEL}:
            continue
        if node.call_type in {CallType.CREATE, CallType.CREATE2, CallType.SELFDESTRUCT}:
            continue
        if not node.to_address:
            continue
        if node.to_address in trusted_addresses:
            continue
        if root_to and node.to_address == root_to and node.depth <= 1:
            continue
        if node.depth <= 1:
            continue
        events.append(
            RuntimeEvent(
                event_type=RuntimeEventType.UNEXPECTED_EXTERNAL_CALL,
                node_id=node.node_id,
                description="Unexpected external call detected deep in the execution trace",
                metadata={
                    "from_address": node.from_address,
                    "to_address": node.to_address,
                    "selector": node.selector,
                    "depth": node.depth,
                },
            )
        )
    return events


def _looks_like_flash_loan(node: object) -> bool:
    selector = getattr(node, "selector", None)
    if not selector:
        return False
    return selector.startswith("ab") or selector.startswith("42")


def _dedupe_events(events: list[RuntimeEvent]) -> tuple[RuntimeEvent, ...]:
    seen: set[tuple[str, str]] = set()
    unique: list[RuntimeEvent] = []
    for event in sorted(events, key=lambda item: (item.event_type.value, item.node_id)):
        key = (event.event_type.value, event.node_id)
        if key in seen:
            continue
        seen.add(key)
        unique.append(event)
    return tuple(unique)
