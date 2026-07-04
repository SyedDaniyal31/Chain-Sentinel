"""Etherscan-compatible block explorer source provider (M4.2 / M5.0)."""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from app.blockchain.chain_registry import ChainRegistry, get_chain_registry
from app.blockchain.contract_source_provider import (
    ContractMetadata,
    ContractSourceProvider,
    VerifiedContractSource,
)

logger = logging.getLogger(__name__)


class ExplorerSourceProvider(ContractSourceProvider):
    """Fetch verified source via Etherscan-compatible explorer APIs (Etherscan, Basescan, etc.)."""

    def __init__(
        self,
        api_key: str,
        *,
        registry: ChainRegistry | None = None,
        timeout_seconds: int = 15,
    ) -> None:
        self._api_key = api_key
        self._registry = registry or get_chain_registry()
        self._timeout_seconds = timeout_seconds

    async def get_verified_source(
        self,
        contract_address: str,
        chain_id: int,
    ) -> VerifiedContractSource | None:
        entry = await self._fetch_source_entry(contract_address, chain_id)
        if entry is None:
            return None
        return self._parse_verified_source(entry)

    async def fetch_abi(
        self,
        contract_address: str,
        chain_id: int,
    ) -> list[dict[str, Any]] | None:
        verified = await self.get_verified_source(contract_address, chain_id)
        return verified.abi if verified else None

    async def fetch_compiler_version(
        self,
        contract_address: str,
        chain_id: int,
    ) -> str | None:
        entry = await self._fetch_source_entry(contract_address, chain_id)
        if entry is None:
            return None
        compiler = str(entry.get("CompilerVersion") or "").strip()
        return compiler or None

    async def fetch_contract_metadata(
        self,
        contract_address: str,
        chain_id: int,
    ) -> ContractMetadata | None:
        entry = await self._fetch_source_entry(contract_address, chain_id)
        if entry is None:
            return None
        return self._parse_metadata(entry)

    async def _fetch_source_entry(
        self,
        contract_address: str,
        chain_id: int,
    ) -> dict[str, Any] | None:
        base_url = self._registry.get_explorer_api_base(chain_id)
        if base_url is None:
            logger.debug("No explorer API configured for chain_id=%s", chain_id)
            return None

        params = {
            "module": "contract",
            "action": "getsourcecode",
            "address": contract_address,
            "apikey": self._api_key,
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
                response = await client.get(base_url, params=params)
                response.raise_for_status()
                payload = response.json()
        except Exception:
            logger.info(
                "Verified source lookup failed for %s on chain %s",
                contract_address,
                chain_id,
            )
            return None

        if payload.get("status") != "1":
            return None

        results = payload.get("result")
        if not isinstance(results, list) or not results:
            return None

        entry = results[0]
        if not isinstance(entry, dict):
            return None

        source_code = str(entry.get("SourceCode") or "").strip()
        if not source_code or source_code == "Contract source code not verified":
            return None

        return entry

    def _parse_verified_source(self, entry: dict[str, Any]) -> VerifiedContractSource:
        source_code = str(entry.get("SourceCode") or "").strip()
        metadata = self._parse_metadata(entry)
        abi = self._parse_abi(entry)

        return VerifiedContractSource(
            contract_name=str(entry.get("ContractName") or metadata.contract_name),
            source_code=source_code,
            abi=abi,
            is_proxy=metadata.is_proxy,
            implementation_address=metadata.implementation_address,
            compiler_version=metadata.compiler_version,
            metadata=metadata,
        )

    def _parse_metadata(self, entry: dict[str, Any]) -> ContractMetadata:
        proxy_flag = str(entry.get("Proxy") or "0") == "1"
        implementation = entry.get("Implementation")
        implementation_address = (
            str(implementation).lower()
            if isinstance(implementation, str) and implementation.startswith("0x")
            else None
        )
        optimization = str(entry.get("OptimizationUsed") or "0") == "1"
        runs_raw = entry.get("Runs")
        optimization_runs = int(runs_raw) if str(runs_raw or "").isdigit() else None

        return ContractMetadata(
            contract_name=str(entry.get("ContractName") or "Unknown"),
            compiler_version=str(entry.get("CompilerVersion") or "").strip() or None,
            optimization_enabled=optimization,
            optimization_runs=optimization_runs,
            evm_version=str(entry.get("EVMVersion") or "").strip() or None,
            license_type=str(entry.get("LicenseType") or "").strip() or None,
            is_proxy=proxy_flag,
            implementation_address=implementation_address,
            runs=str(entry.get("Runs") or "").strip() or None,
            constructor_arguments=str(entry.get("ConstructorArguments") or "").strip() or None,
            library=str(entry.get("Library") or "").strip() or None,
            swarm_source=str(entry.get("SwarmSource") or "").strip() or None,
        )

    def _parse_abi(self, entry: dict[str, Any]) -> list[dict[str, Any]] | None:
        abi_raw = entry.get("ABI")
        if not isinstance(abi_raw, str) or not abi_raw.startswith("["):
            return None
        try:
            parsed = json.loads(abi_raw)
        except json.JSONDecodeError:
            logger.debug("Malformed ABI JSON in explorer response")
            return None
        if isinstance(parsed, list):
            return parsed
        return None


# Backward-compatible aliases from M4.2.
EtherscanSourceProvider = ExplorerSourceProvider
EtherscanContractSourceProvider = ExplorerSourceProvider
