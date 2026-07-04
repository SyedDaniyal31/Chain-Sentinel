"""Normalize provider-specific state transition payloads (M9.3)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from app.blockchain.runtime.state.models import (
    BalanceAssetType,
    RawAllowanceDiff,
    RawBalanceDiff,
    RawStateLog,
    RawStateTransition,
    RawStorageDiff,
    RawSupplyDiff,
)


class StateTransitionDecoder:
    """Decode archive, Tenderly, Foundry, and RPC state payloads."""

    @classmethod
    def decode(
        cls,
        payload: Mapping[str, Any] | RawStateTransition,
        *,
        transaction_hash: str,
        provider_name: str = "decoded",
        chain_id: int | None = None,
    ) -> RawStateTransition:
        if isinstance(payload, RawStateTransition):
            return payload

        storage = tuple(
            cls._decode_storage(item)
            for item in payload.get("storage_diffs") or payload.get("storageDiffs") or []
        )
        balances = tuple(
            cls._decode_balance(item)
            for item in payload.get("balance_diffs") or payload.get("balanceDiffs") or []
        )
        allowances = tuple(
            cls._decode_allowance(item)
            for item in payload.get("allowance_diffs") or payload.get("allowanceDiffs") or []
        )
        supplies = tuple(
            cls._decode_supply(item)
            for item in payload.get("supply_diffs") or payload.get("supplyDiffs") or []
        )
        logs = tuple(
            cls._decode_log(item)
            for item in payload.get("logs") or payload.get("events") or []
        )

        return RawStateTransition(
            transaction_hash=transaction_hash.lower(),
            block_number=_optional_int(payload.get("blockNumber") or payload.get("block_number")),
            storage_diffs=storage,
            balance_diffs=balances,
            allowance_diffs=allowances,
            supply_diffs=supplies,
            logs=logs,
            provider_name=str(payload.get("provider_name", provider_name)),
            chain_id=chain_id,
        )

    @staticmethod
    def _decode_storage(item: Mapping[str, Any]) -> RawStorageDiff:
        return RawStorageDiff(
            contract_address=_normalize_address(item.get("contract") or item.get("contract_address")),
            slot=_normalize_slot(item.get("slot")),
            before=_normalize_word(item.get("before") or item.get("pre")),
            after=_normalize_word(item.get("after") or item.get("post")),
        )

    @staticmethod
    def _decode_balance(item: Mapping[str, Any]) -> RawBalanceDiff:
        asset = str(item.get("asset_type") or item.get("assetType") or "erc20").lower()
        asset_type = {
            "native": BalanceAssetType.NATIVE,
            "eth": BalanceAssetType.NATIVE,
            "erc20": BalanceAssetType.ERC20,
            "erc721": BalanceAssetType.ERC721,
            "erc1155": BalanceAssetType.ERC1155,
        }.get(asset, BalanceAssetType.ERC20)
        contract = item.get("contract") or item.get("contract_address") or item.get("token")
        return RawBalanceDiff(
            asset_type=asset_type,
            contract_address=_normalize_optional_address(contract),
            account_address=_normalize_address(item.get("account") or item.get("account_address")),
            before=_normalize_int(item.get("before")),
            after=_normalize_int(item.get("after")),
            token_id=_optional_int(item.get("token_id") or item.get("tokenId")),
        )

    @staticmethod
    def _decode_allowance(item: Mapping[str, Any]) -> RawAllowanceDiff:
        return RawAllowanceDiff(
            token_address=_normalize_address(item.get("token") or item.get("token_address")),
            owner_address=_normalize_address(item.get("owner") or item.get("owner_address")),
            spender_address=_normalize_address(item.get("spender") or item.get("spender_address")),
            before=_normalize_int(item.get("before")),
            after=_normalize_int(item.get("after")),
        )

    @staticmethod
    def _decode_supply(item: Mapping[str, Any]) -> RawSupplyDiff:
        return RawSupplyDiff(
            token_address=_normalize_address(item.get("token") or item.get("token_address")),
            before=_normalize_int(item.get("before")),
            after=_normalize_int(item.get("after")),
        )

    @staticmethod
    def _decode_log(item: Mapping[str, Any]) -> RawStateLog:
        topics_raw = item.get("topics") or ()
        topics = tuple(
            topic.lower() if isinstance(topic, str) else f"0x{bytes(topic).hex()}"
            for topic in topics_raw
        )
        data = _normalize_bytes(item.get("data"))
        return RawStateLog(
            contract_address=_normalize_address(item.get("address") or item.get("contract_address")),
            topics=topics,
            data=data,
        )


def _normalize_address(value: Any) -> str:
    if value is None:
        return "0x0000000000000000000000000000000000000000"
    text = str(value).lower()
    return text if text.startswith("0x") else f"0x{text}"


def _normalize_optional_address(value: Any) -> str | None:
    if value is None:
        return None
    address = _normalize_address(value)
    if address == "0x0000000000000000000000000000000000000000":
        return None
    return address


def _normalize_slot(value: Any) -> str:
    if value is None:
        return "0x" + ("0" * 64)
    text = str(value).lower()
    if text.startswith("0x"):
        return text
    return "0x" + text.zfill(64)


def _normalize_word(value: Any) -> str:
    return _normalize_slot(value)


def _normalize_int(value: Any, *, default: int = 0) -> int:
    if value is None:
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        return int(value, 16) if value.startswith("0x") else int(value)
    return int(value)


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    return _normalize_int(value)


def _normalize_bytes(value: Any) -> bytes:
    if value is None:
        return b""
    if isinstance(value, bytes):
        return value
    text = str(value)
    if text in {"", "0x", "0X"}:
        return b""
    return bytes.fromhex(text[2:] if text.startswith("0x") else text)
