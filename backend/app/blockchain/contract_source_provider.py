"""M4.2 contract source provider abstraction."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class ContractMetadata:
    """Block explorer metadata for a verified contract."""

    contract_name: str = "Unknown"
    compiler_version: str | None = None
    optimization_enabled: bool | None = None
    optimization_runs: int | None = None
    evm_version: str | None = None
    license_type: str | None = None
    is_proxy: bool = False
    implementation_address: str | None = None
    runs: str | None = None
    constructor_arguments: str | None = None
    library: str | None = None
    swarm_source: str | None = None


@dataclass(frozen=True, slots=True)
class VerifiedContractSource:
    """Verified source bundle returned by a ContractSourceProvider."""

    contract_name: str
    source_code: str
    abi: list[dict[str, Any]] | None
    is_proxy: bool = False
    implementation_address: str | None = None
    compiler_version: str | None = None
    metadata: ContractMetadata | None = None

    @property
    def is_verified(self) -> bool:
        return bool(self.source_code.strip())


class ContractSourceProvider(ABC):
    """Pluggable provider for verified contract source, ABI, and metadata."""

    @abstractmethod
    async def get_verified_source(
        self,
        contract_address: str,
        chain_id: int,
    ) -> VerifiedContractSource | None:
        """Return verified source when available; None when unverified or unsupported."""


class NullContractSourceProvider(ContractSourceProvider):
    """Default no-op provider — always defers to bytecode heuristics."""

    async def get_verified_source(
        self,
        contract_address: str,
        chain_id: int,
    ) -> VerifiedContractSource | None:
        return None
