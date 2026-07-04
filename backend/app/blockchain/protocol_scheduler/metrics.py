"""Protocol scan metrics collection (M8.3)."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.blockchain.protocol_scheduler.models import ProtocolScanMetrics


@dataclass(slots=True)
class ProtocolScanMetricsCollector:
    """Mutable metrics accumulator for a single protocol scan run."""

    nodes_scanned: int = 0
    parallel_batches_executed: int = 0
    retry_count: int = 0
    _node_durations_ms: list[float] = field(default_factory=list)

    def record_batch(self) -> None:
        self.parallel_batches_executed += 1

    def record_node(self, *, duration_ms: float, retry_count: int) -> None:
        self.nodes_scanned += 1
        self._node_durations_ms.append(duration_ms)
        self.retry_count += retry_count

    def build(self, total_duration_ms: float) -> ProtocolScanMetrics:
        average_node_duration_ms = 0.0
        if self._node_durations_ms:
            average_node_duration_ms = sum(self._node_durations_ms) / len(
                self._node_durations_ms
            )
        return ProtocolScanMetrics(
            nodes_scanned=self.nodes_scanned,
            parallel_batches_executed=self.parallel_batches_executed,
            total_duration_ms=total_duration_ms,
            average_node_duration_ms=average_node_duration_ms,
            retry_count=self.retry_count,
        )
