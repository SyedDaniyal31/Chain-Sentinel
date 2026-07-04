"""Execution revert analysis (M9.2)."""

from __future__ import annotations

from app.blockchain.runtime.calltrace.models import RevertAnalysis, RevertFinding, RuntimeCallGraph


class RevertAnalyzer:
    """Capture revert reasons and failing execution paths."""

    def analyze(self, graph: RuntimeCallGraph) -> RevertAnalysis:
        findings: list[RevertFinding] = []
        nodes_by_id = {node.node_id: node for node in graph.nodes}

        for node in graph.nodes:
            if not node.error and not node.revert_reason:
                continue
            findings.append(
                RevertFinding(
                    node_id=node.node_id,
                    contract_address=node.to_address or node.from_address,
                    failing_function=node.selector,
                    revert_reason=node.revert_reason or node.error,
                    call_depth=node.depth,
                    execution_path=_execution_path(node.node_id, nodes_by_id),
                )
            )

        sorted_findings = tuple(sorted(findings, key=lambda item: (item.call_depth, item.node_id)))
        return RevertAnalysis(has_revert=bool(sorted_findings), findings=sorted_findings)


def _execution_path(node_id: str, nodes_by_id: dict[str, object]) -> tuple[str, ...]:
    path: list[str] = []
    current_id: str | None = node_id
    while current_id is not None:
        path.append(current_id)
        node = nodes_by_id.get(current_id)
        if node is None:
            break
        current_id = getattr(node, "parent_id", None)
    return tuple(reversed(path))
