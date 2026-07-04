"""State transition provider abstractions (M9.3)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable, Mapping
from typing import Any

from app.blockchain.runtime.state.models import RawStateTransition


class StateTransitionProvider(ABC):
    """Provider-agnostic interface for transaction state transition data."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Human-readable provider identifier."""

    @abstractmethod
    async def get_state_transition(
        self,
        transaction_hash: str,
        *,
        chain_id: int,
        block_number: int | None = None,
    ) -> RawStateTransition:
        """Fetch normalized pre/post state transition data for a transaction."""


class StaticStateTransitionProvider(StateTransitionProvider):
    """In-memory provider for tests and offline replay."""

    def __init__(
        self,
        transitions: dict[str, RawStateTransition] | None = None,
        *,
        provider_name: str = "static",
    ) -> None:
        self._transitions = transitions or {}
        self._provider_name = provider_name

    @property
    def provider_name(self) -> str:
        return self._provider_name

    def register(self, transition: RawStateTransition) -> None:
        self._transitions[transition.transaction_hash.lower()] = transition

    async def get_state_transition(
        self,
        transaction_hash: str,
        *,
        chain_id: int,
        block_number: int | None = None,
    ) -> RawStateTransition:
        normalized = transaction_hash.lower()
        transition = self._transitions.get(normalized)
        if transition is None:
            raise KeyError(f"No static state transition registered for {transaction_hash}")
        return RawStateTransition(
            transaction_hash=transition.transaction_hash,
            block_number=block_number or transition.block_number,
            storage_diffs=transition.storage_diffs,
            balance_diffs=transition.balance_diffs,
            allowance_diffs=transition.allowance_diffs,
            supply_diffs=transition.supply_diffs,
            logs=transition.logs,
            provider_name=self._provider_name,
            chain_id=chain_id,
        )


class MappingStateTransitionProvider(StateTransitionProvider):
    """Provider backed by an async loader returning raw provider payloads."""

    def __init__(
        self,
        loader: Callable[..., Awaitable[Mapping[str, Any]]],
        *,
        provider_name: str = "mapping",
    ) -> None:
        self._loader = loader
        self._provider_name = provider_name

    @property
    def provider_name(self) -> str:
        return self._provider_name

    async def get_state_transition(
        self,
        transaction_hash: str,
        *,
        chain_id: int,
        block_number: int | None = None,
    ) -> RawStateTransition:
        payload = await self._loader(
            transaction_hash,
            chain_id=chain_id,
            block_number=block_number,
        )
        from app.blockchain.runtime.state.state_decoder import StateTransitionDecoder

        return StateTransitionDecoder.decode(
            payload,
            transaction_hash=transaction_hash,
            provider_name=self._provider_name,
            chain_id=chain_id,
        )
