"""Protocol snapshot builder (M10.2)."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any

from app.blockchain.continuous.change_detection.models import ContractSnapshot, ProtocolSnapshot
from app.blockchain.continuous.change_detection.snapshot import normalize_address, snapshot_id
from app.blockchain.continuous.protocol_subscription import watch_id


class SnapshotBuilder:
    """Build immutable protocol snapshots from normalized payloads."""

    def build(
        self,
        payload: Mapping[str, Any],
        *,
        captured_at: datetime | None = None,
    ) -> ProtocolSnapshot:
        chain_id = int(payload["chain_id"])
        root_address = normalize_address(str(payload["root_address"])) or ""
        watch = str(payload.get("watch_id") or watch_id(chain_id, root_address))
        moment = captured_at or _parse_datetime(payload.get("captured_at"))
        contracts = tuple(self._build_contract(item) for item in payload.get("contracts", ()))
        contracts = tuple(sorted(contracts, key=lambda item: item.address))
        built = ProtocolSnapshot(
            snapshot_id=str(payload.get("snapshot_id") or snapshot_id(watch, moment)),
            watch_id=watch,
            chain_id=chain_id,
            root_address=root_address,
            captured_at=moment,
            contracts=contracts,
            dependency_fingerprint=str(payload.get("dependency_fingerprint", "")),
            liquidity_fingerprint=str(payload.get("liquidity_fingerprint", "")),
            runtime_fingerprint=str(payload.get("runtime_fingerprint", "")),
            metadata=dict(payload.get("metadata") or {}),
        )
        return built

    def build_contract(self, payload: Mapping[str, Any]) -> ContractSnapshot:
        return self._build_contract(payload)

    def _build_contract(self, payload: Mapping[str, Any]) -> ContractSnapshot:
        address = normalize_address(str(payload["address"])) or ""
        return ContractSnapshot(
            address=address,
            proxy_implementation=normalize_address(payload.get("proxy_implementation")),
            owner=normalize_address(payload.get("owner")),
            proxy_admin=normalize_address(payload.get("proxy_admin")),
            timelock=normalize_address(payload.get("timelock")),
            governor=normalize_address(payload.get("governor")),
            treasury=normalize_address(payload.get("treasury")),
            bytecode_hash=_optional_str(payload.get("bytecode_hash")),
            abi_hash=_optional_str(payload.get("abi_hash")),
            metadata=dict(payload.get("metadata") or {}),
        )


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    return str(value)


def _parse_datetime(value: object) -> datetime:
    if isinstance(value, datetime):
        return value
    if value is None:
        from app.blockchain.continuous.change_detection.snapshot import utc_now

        return utc_now()
    return datetime.fromisoformat(str(value))
