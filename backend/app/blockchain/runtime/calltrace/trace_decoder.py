"""Normalize provider-specific execution traces (M9.2)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from app.blockchain.runtime.calltrace.models import CallType, RawExecutionTrace, RawTraceNode


class TraceDecoder:
    """Decode nested trace payloads from RPC providers into RawTraceNode trees."""

    @classmethod
    def decode_trace(
        cls,
        payload: Mapping[str, Any] | RawTraceNode,
        *,
        transaction_hash: str,
        provider_name: str = "decoded",
        chain_id: int | None = None,
    ) -> RawExecutionTrace:
        if isinstance(payload, RawTraceNode):
            root = payload
        elif "root" in payload and isinstance(payload["root"], RawTraceNode):
            root = payload["root"]
        elif "result" in payload:
            root = cls.decode_node(payload["result"])
        else:
            root = cls.decode_node(payload)

        return RawExecutionTrace(
            transaction_hash=transaction_hash.lower(),
            root=root,
            provider_name=provider_name,
            chain_id=chain_id,
        )

    @classmethod
    def decode_node(cls, node: Mapping[str, Any] | RawTraceNode) -> RawTraceNode:
        if isinstance(node, RawTraceNode):
            return node

        call_type = _normalize_call_type(node.get("type") or node.get("callType") or "CALL")
        children_payload = node.get("calls") or node.get("children") or []
        children = tuple(cls.decode_node(child) for child in children_payload)

        return RawTraceNode(
            call_type=call_type,
            from_address=_normalize_address(node.get("from") or node.get("fromAddress")),
            to_address=_normalize_optional_address(node.get("to") or node.get("toAddress")),
            value_wei=_normalize_int(node.get("value"), default=0),
            gas=_normalize_int(node.get("gas"), default=0),
            gas_used=_normalize_int(node.get("gasUsed") or node.get("gas_used"), default=0),
            input=_normalize_bytes(node.get("input") or node.get("callData")),
            output=_normalize_bytes(node.get("output") or node.get("returnData")),
            error=_normalize_optional_str(node.get("error")),
            revert_reason=_normalize_optional_str(
                node.get("revertReason") or node.get("revert_reason")
            ),
            children=children,
        )


def _normalize_call_type(value: Any) -> CallType:
    text = str(value).upper().replace("-", "").replace("_", "")
    aliases = {
        "SUICIDE": CallType.SELFDESTRUCT,
        "SELFDESTRUCT": CallType.SELFDESTRUCT,
        "DELEGATECALL": CallType.DELEGATECALL,
        "STATICCALL": CallType.STATICCALL,
        "CALLCODE": CallType.CALLCODE,
        "CREATE2": CallType.CREATE2,
        "CREATE": CallType.CREATE,
        "CALL": CallType.CALL,
    }
    return aliases.get(text, CallType.CALL)


def _normalize_address(value: Any) -> str:
    if value is None:
        return "0x0000000000000000000000000000000000000000"
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
    address = _normalize_address(value)
    if address == "0x0000000000000000000000000000000000000000":
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


def _normalize_optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
