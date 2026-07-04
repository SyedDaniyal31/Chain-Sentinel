"""Retry policy for protocol node scans (M8.3)."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TypeVar

T = TypeVar("T")


class RetryExhaustedError(Exception):
    """Raised when all retry attempts for a node scan are exhausted."""


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    """Bounded retry configuration for node scan execution."""

    max_attempts: int = 3
    delay_seconds: float = 0.0

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")


async def execute_with_retry(
    operation: Callable[[], Awaitable[T]],
    policy: RetryPolicy,
) -> tuple[T, int]:
    """
    Execute an async operation with bounded retries.

    Returns:
        Tuple of (result, retry_count) where retry_count is the number of
        failed attempts before the successful one.
    """
    last_error: Exception | None = None

    for attempt in range(policy.max_attempts):
        try:
            result = await operation()
            return result, attempt
        except Exception as exc:
            last_error = exc
            if attempt + 1 < policy.max_attempts and policy.delay_seconds > 0:
                await asyncio.sleep(policy.delay_seconds)

    assert last_error is not None
    raise RetryExhaustedError(str(last_error)) from last_error
