"""Worker pool abstractions for parallel node execution (M8.3)."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Sequence
from typing import Protocol, TypeVar

T = TypeVar("T")


class WorkerPool(Protocol):
    """Provider-agnostic worker pool for executing scan tasks in parallel."""

    async def run_batch(self, tasks: Sequence[Awaitable[T]]) -> list[T]:
        """Execute a batch of awaitables with bounded concurrency."""


class LocalAsyncWorkerPool:
    """In-process asyncio worker pool backed by a semaphore."""

    def __init__(self, max_workers: int = 4) -> None:
        if max_workers < 1:
            raise ValueError("max_workers must be at least 1")
        self._max_workers = max_workers

    async def run_batch(self, tasks: Sequence[Awaitable[T]]) -> list[T]:
        if not tasks:
            return []

        semaphore = asyncio.Semaphore(self._max_workers)

        async def _run(task: Awaitable[T]) -> T:
            async with semaphore:
                return await task

        return list(await asyncio.gather(*(_run(task) for task in tasks)))
