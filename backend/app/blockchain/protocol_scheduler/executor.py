"""Node scan executor abstractions (M8.3)."""

from __future__ import annotations

import time
from dataclasses import replace
from typing import Protocol

from app.blockchain.protocol_scheduler.models import NodeScanResult, NodeScanStatus, utc_now
from app.blockchain.protocol_scheduler.retry import RetryExhaustedError, RetryPolicy, execute_with_retry
from app.schemas.scan_result import ContractAnalysisData
from app.services.contract_analyzer import ContractAnalyzer


class NodeScanExecutor(Protocol):
    """Provider-agnostic contract scan executor for protocol graph nodes."""

    async def analyze_node(self, address: str) -> ContractAnalysisData:
        """Analyze a single protocol node address."""


class ContractAnalyzerNodeScanExecutor:
    """Adapter that delegates node scans to the existing ContractAnalyzer."""

    def __init__(self, analyzer: ContractAnalyzer) -> None:
        self._analyzer = analyzer

    async def analyze_node(self, address: str) -> ContractAnalysisData:
        return await self._analyzer.analyze(address)


class NodeScanWorker:
    """Executes a single protocol node scan with retry and timing."""

    def __init__(
        self,
        executor: NodeScanExecutor,
        retry_policy: RetryPolicy | None = None,
    ) -> None:
        self._executor = executor
        self._retry_policy = retry_policy or RetryPolicy()

    async def scan(self, address: str) -> NodeScanResult:
        started_at = utc_now()
        start_perf = time.perf_counter()

        try:
            analysis, retry_count = await execute_with_retry(
                lambda: self._executor.analyze_node(address),
                self._retry_policy,
            )
        except RetryExhaustedError as exc:
            duration_ms = (time.perf_counter() - start_perf) * 1000
            return NodeScanResult(
                address=address,
                status=NodeScanStatus.FAILED,
                error=str(exc),
                duration_ms=duration_ms,
                retry_count=max(0, self._retry_policy.max_attempts - 1),
                started_at=started_at,
                completed_at=utc_now(),
            )

        duration_ms = (time.perf_counter() - start_perf) * 1000
        return NodeScanResult(
            address=address,
            status=NodeScanStatus.COMPLETED,
            analysis=analysis,
            duration_ms=duration_ms,
            retry_count=retry_count,
            started_at=started_at,
            completed_at=utc_now(),
        )

    @staticmethod
    def skipped(address: str, *, reason: str) -> NodeScanResult:
        return NodeScanResult(
            address=address,
            status=NodeScanStatus.SKIPPED,
            error=reason,
            completed_at=utc_now(),
        )

    @staticmethod
    def merge_result(
        current: NodeScanResult,
        updated: NodeScanResult,
    ) -> NodeScanResult:
        return replace(
            current,
            status=updated.status,
            analysis=updated.analysis,
            error=updated.error,
            duration_ms=updated.duration_ms,
            retry_count=updated.retry_count,
            started_at=updated.started_at or current.started_at,
            completed_at=updated.completed_at,
        )
