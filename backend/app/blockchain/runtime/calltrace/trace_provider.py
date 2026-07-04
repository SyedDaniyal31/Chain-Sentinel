"""Execution trace provider abstractions (M9.2)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.blockchain.runtime.calltrace.models import RawExecutionTrace, RawTraceNode


class TraceProvider(ABC):
    """Provider-agnostic interface for fetching transaction execution traces."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Human-readable provider identifier."""

    @abstractmethod
    async def get_execution_trace(
        self,
        transaction_hash: str,
        *,
        chain_id: int,
    ) -> RawExecutionTrace:
        """Fetch and normalize an execution trace for a transaction hash."""


class StaticTraceProvider(TraceProvider):
    """In-memory trace provider for tests and offline analysis."""

    def __init__(
        self,
        traces: dict[str, RawExecutionTrace] | None = None,
        *,
        provider_name: str = "static",
    ) -> None:
        self._traces = traces or {}
        self._provider_name = provider_name

    @property
    def provider_name(self) -> str:
        return self._provider_name

    def register(self, trace: RawExecutionTrace) -> None:
        self._traces[trace.transaction_hash.lower()] = trace

    async def get_execution_trace(
        self,
        transaction_hash: str,
        *,
        chain_id: int,
    ) -> RawExecutionTrace:
        normalized = transaction_hash.lower()
        trace = self._traces.get(normalized)
        if trace is None:
            raise KeyError(f"No static trace registered for {transaction_hash}")
        return RawExecutionTrace(
            transaction_hash=trace.transaction_hash,
            root=trace.root,
            provider_name=self._provider_name,
            chain_id=chain_id,
        )


class MappingTraceProvider(TraceProvider):
    """Trace provider that resolves traces from a generic async loader."""

    def __init__(
        self,
        loader: Any,
        *,
        provider_name: str = "mapping",
    ) -> None:
        self._loader = loader
        self._provider_name = provider_name

    @property
    def provider_name(self) -> str:
        return self._provider_name

    async def get_execution_trace(
        self,
        transaction_hash: str,
        *,
        chain_id: int,
    ) -> RawExecutionTrace:
        payload = await self._loader(transaction_hash, chain_id=chain_id)
        from app.blockchain.runtime.calltrace.trace_decoder import TraceDecoder

        root = TraceDecoder.decode_node(payload)
        return RawExecutionTrace(
            transaction_hash=transaction_hash.lower(),
            root=root,
            provider_name=self._provider_name,
            chain_id=chain_id,
        )
