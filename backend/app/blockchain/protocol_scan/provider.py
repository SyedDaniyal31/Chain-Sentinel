"""Provider-agnostic protocol discovery interfaces (M8.1)."""

from __future__ import annotations

import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from web3 import AsyncWeb3

from app.blockchain.contract_source_provider import (
    ContractSourceProvider,
    NullContractSourceProvider,
    VerifiedContractSource,
)
from app.blockchain.protocol.defi_registry import source_contains_marker
from app.core.validators import normalize_eth_address
from app.services.admin_analyzer import AdminAnalyzer
from app.services.proxy_analyzer import ProxyAnalyzer

logger = logging.getLogger(__name__)

_ADDRESS_PATTERN = re.compile(r"0x[a-fA-F0-9]{40}")
_IGNORED_ADDRESSES = {
    "0x0000000000000000000000000000000000000000",
    "0x000000000000000000000000000000000000dead",
}


@dataclass(frozen=True, slots=True)
class ContractProbeResult:
    """Normalized on-chain probe output for a single contract address."""

    address: str
    chain_id: int
    bytecode: bytes
    verified_source: VerifiedContractSource | None = None
    implementation_address: str | None = None
    admin_address: str | None = None
    is_timelock: bool = False
    linked_addresses: tuple[str, ...] = field(default_factory=tuple)


class ProtocolDiscoveryProvider(ABC):
    """Pluggable provider for contract probing during protocol discovery."""

    @abstractmethod
    async def probe_contract(self, address: str, chain_id: int) -> ContractProbeResult:
        """Collect bytecode, verified source, proxy metadata, and linked addresses."""


class OnChainProtocolDiscoveryProvider(ProtocolDiscoveryProvider):
    """Default provider using Web3 RPC and existing ChainSentinel analyzers."""

    def __init__(
        self,
        web3: AsyncWeb3,
        *,
        source_provider: ContractSourceProvider | None = None,
        proxy_analyzer: ProxyAnalyzer | None = None,
        admin_analyzer: AdminAnalyzer | None = None,
    ) -> None:
        self._web3 = web3
        self._source_provider = source_provider or NullContractSourceProvider()
        self._proxy_analyzer = proxy_analyzer or ProxyAnalyzer(web3)
        self._admin_analyzer = admin_analyzer or AdminAnalyzer(web3)

    async def probe_contract(self, address: str, chain_id: int) -> ContractProbeResult:
        normalized = normalize_eth_address(address)
        checksum = AsyncWeb3.to_checksum_address(normalized)

        bytecode = bytes(await self._web3.eth.get_code(checksum))
        verified_source = await self._source_provider.get_verified_source(normalized, chain_id)

        implementation_address: str | None = None
        admin_address: str | None = None
        if bytecode:
            try:
                proxy = await self._proxy_analyzer.analyze(normalized)
                implementation_address = proxy.implementation_address
            except Exception:
                logger.debug("Proxy probe failed for %s", normalized, exc_info=True)

            if verified_source and verified_source.implementation_address:
                implementation_address = normalize_eth_address(verified_source.implementation_address)

            try:
                admin = await self._admin_analyzer.analyze(normalized)
                admin_address = admin.admin_address
            except Exception:
                logger.debug("Admin probe failed for %s", normalized, exc_info=True)

        source_code = verified_source.source_code if verified_source else None
        is_timelock = _detect_timelock(bytecode, source_code)
        linked_addresses = _extract_linked_addresses(source_code, verified_source.abi if verified_source else None)

        return ContractProbeResult(
            address=normalized,
            chain_id=chain_id,
            bytecode=bytecode,
            verified_source=verified_source,
            implementation_address=implementation_address,
            admin_address=admin_address,
            is_timelock=is_timelock,
            linked_addresses=linked_addresses,
        )


def _detect_timelock(bytecode: bytes, source_code: str | None) -> bool:
    markers = ("TIMELOCKCONTROLLER", "TIMELOCK CONTROLLER", "MINIMUMDELAY", "schedule(")
    if source_contains_marker(source_code, markers):
        return True
    upper = bytecode.hex().upper()
    return "TIMELOCK" in upper or "4756574F524E" in upper  # governor hex fragment fallback


def _extract_linked_addresses(
    source_code: str | None,
    abi: list[dict] | None,
) -> tuple[str, ...]:
    addresses: set[str] = set()
    if source_code:
        for match in _ADDRESS_PATTERN.findall(source_code):
            normalized = match.lower()
            if normalized not in _IGNORED_ADDRESSES:
                addresses.add(normalized)
    if abi:
        for entry in abi:
            for input_item in entry.get("inputs", []):
                if input_item.get("type") == "address" and isinstance(input_item.get("internalType"), str):
                    continue
    return tuple(sorted(addresses))
