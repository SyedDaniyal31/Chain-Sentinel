"""Ethereum transaction envelope decoder (M9.1)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from app.blockchain.runtime.transaction.models import TransactionFormat, TransactionMetadata


class TransactionDecoder:
    """Decode legacy, EIP-1559, and contract-creation transactions."""

    @classmethod
    def decode(cls, raw_transaction: Mapping[str, Any]) -> TransactionMetadata:
        tx_hash = _normalize_hash(raw_transaction.get("hash"))
        from_address = _normalize_address(raw_transaction.get("from") or raw_transaction.get("fromAddress"))
        to_address = _normalize_optional_address(raw_transaction.get("to"))
        value_wei = _normalize_int(raw_transaction.get("value"), default=0)
        nonce = _normalize_int(raw_transaction.get("nonce"), default=0)
        gas = _normalize_int(raw_transaction.get("gas"), default=0)
        gas_price = _optional_int(raw_transaction.get("gasPrice"))
        max_fee = _optional_int(raw_transaction.get("maxFeePerGas"))
        max_priority = _optional_int(raw_transaction.get("maxPriorityFeePerGas"))
        chain_id = _optional_int(raw_transaction.get("chainId"))
        block_number = _optional_int(raw_transaction.get("blockNumber"))
        calldata = _normalize_bytes(raw_transaction.get("input") or raw_transaction.get("data"))

        tx_type = _normalize_int(raw_transaction.get("type"), default=0)
        if to_address is None:
            transaction_format = TransactionFormat.CONTRACT_CREATION
        elif tx_type == 2 or max_fee is not None:
            transaction_format = TransactionFormat.EIP1559
        else:
            transaction_format = TransactionFormat.LEGACY

        return TransactionMetadata(
            transaction_hash=tx_hash,
            chain_id=chain_id,
            from_address=from_address,
            to_address=to_address,
            value_wei=value_wei,
            nonce=nonce,
            gas=gas,
            gas_price_wei=gas_price,
            max_fee_per_gas_wei=max_fee,
            max_priority_fee_per_gas_wei=max_priority,
            transaction_format=transaction_format,
            block_number=block_number,
            input_size=len(calldata),
        )

    @staticmethod
    def extract_calldata(raw_transaction: Mapping[str, Any]) -> bytes:
        return _normalize_bytes(raw_transaction.get("input") or raw_transaction.get("data"))


def _normalize_hash(value: Any) -> str:
    if value is None:
        return "0x" + ("0" * 64)
    if hasattr(value, "hex"):
        hex_value = value.hex()
        return hex_value if hex_value.startswith("0x") else f"0x{hex_value}"
    text = str(value).lower()
    return text if text.startswith("0x") else f"0x{text}"


def _normalize_address(value: Any) -> str:
    if value is None:
        raise ValueError("transaction missing from address")
    if hasattr(value, "hex"):
        hex_value = value.hex()
        address = hex_value if hex_value.startswith("0x") else f"0x{hex_value}"
    else:
        address = str(value).lower()
        if not address.startswith("0x"):
            address = f"0x{address}"
    return address


def _normalize_optional_address(value: Any) -> str | None:
    if value is None:
        return None
    if hasattr(value, "hex"):
        hex_value = value.hex()
        address = hex_value if hex_value.startswith("0x") else f"0x{hex_value}"
    else:
        address = str(value).lower()
        if not address.startswith("0x"):
            address = f"0x{address}"
    if address in {"0x", "0x0", "0x0000000000000000000000000000000000000000"}:
        return None
    return address


def _normalize_int(value: Any, *, default: int = 0) -> int:
    if value is None:
        return default
    if isinstance(value, int):
        return value
    if hasattr(value, "__int__"):
        return int(value)
    if isinstance(value, str):
        return int(value, 16) if value.startswith("0x") else int(value)
    return default


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    return _normalize_int(value)


def _normalize_bytes(value: Any) -> bytes:
    if value is None:
        return b""
    if isinstance(value, bytes):
        return value
    if hasattr(value, "hex"):
        raw = value.hex()
        return bytes.fromhex(raw[2:] if raw.startswith("0x") else raw)
    text = str(value)
    if text in {"", "0x", "0X"}:
        return b""
    return bytes.fromhex(text[2:] if text.startswith("0x") else text)
