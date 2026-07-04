"""Protocol snapshot helpers (M10.2)."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from app.blockchain.continuous.change_detection.models import ContractSnapshot, ProtocolSnapshot


def snapshot_id(watch_id: str, captured_at: datetime) -> str:
    """Build a deterministic snapshot identifier."""
    payload = f"{watch_id}|{captured_at.isoformat()}"
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
    return f"{watch_id}:snapshot:{digest}"


def normalize_address(value: str | None) -> str | None:
    """Normalize an address for comparison."""
    if value is None:
        return None
    normalized = value.lower().removeprefix("0x")
    if len(normalized) != 40:
        return value.lower()
    return "0x" + normalized


def contract_index(contracts: tuple[ContractSnapshot, ...]) -> dict[str, ContractSnapshot]:
    """Index contract snapshots by normalized address."""
    return {item.address.lower(): item for item in contracts}


def contract_addresses(contracts: tuple[ContractSnapshot, ...]) -> tuple[str, ...]:
    """Return sorted contract addresses."""
    return tuple(sorted(item.address.lower() for item in contracts))


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def ensure_protocol_compatibility(baseline: ProtocolSnapshot, current: ProtocolSnapshot) -> None:
    """Validate that snapshots belong to the same watched protocol."""
    if baseline.watch_id != current.watch_id:
        raise ValueError("baseline and current snapshots must share the same watch_id")
    if baseline.chain_id != current.chain_id:
        raise ValueError("baseline and current snapshots must share the same chain_id")
    if baseline.root_address.lower() != current.root_address.lower():
        raise ValueError("baseline and current snapshots must share the same root_address")
