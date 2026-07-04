"""ABI-backed transaction calldata decoder (M9.1)."""

from __future__ import annotations

from typing import Any

from eth_abi import decode as abi_decode
from web3 import Web3

from app.blockchain.contract_source_provider import ContractSourceProvider, NullContractSourceProvider
from app.blockchain.runtime.transaction.models import DecodedArgument, DecodedFunction
from app.blockchain.runtime.transaction.selector_registry import SelectorRegistry


class ABIDecoder:
    """Decode function selectors using verified ABI with registry fallback."""

    def __init__(
        self,
        source_provider: ContractSourceProvider | None = None,
        selector_registry: SelectorRegistry | None = None,
    ) -> None:
        self._source_provider = source_provider or NullContractSourceProvider()
        self._selector_registry = selector_registry or SelectorRegistry()

    async def decode(
        self,
        contract_address: str | None,
        calldata: bytes,
        *,
        chain_id: int,
    ) -> DecodedFunction | None:
        if len(calldata) < 4:
            return None

        selector = calldata[:4].hex()
        arguments_payload = calldata[4:]

        if contract_address:
            verified = await self._source_provider.get_verified_source(contract_address, chain_id)
            if verified and verified.abi:
                decoded = _decode_with_abi(verified.abi, selector, arguments_payload, calldata)
                if decoded is not None:
                    return decoded

        entry = self._selector_registry.lookup(selector)
        if entry is None:
            return DecodedFunction(
                selector=selector,
                function_name="unknown",
                signature=None,
                arguments=(),
                decode_source="selector_unknown",
                raw_calldata=calldata,
            )

        arguments = _decode_with_signature(
            entry=entry,
            signature=entry.signature,
            selector=selector,
            payload=arguments_payload,
        )
        return DecodedFunction(
            selector=selector,
            function_name=entry.function_name,
            signature=entry.signature,
            arguments=arguments,
            decode_source="selector_registry",
            raw_calldata=calldata,
        )


def _decode_with_abi(
    abi: list[dict[str, Any]],
    selector: str,
    payload: bytes,
    raw_calldata: bytes,
) -> DecodedFunction | None:
    for entry in abi:
        if entry.get("type") != "function":
            continue
        name = entry.get("name")
        inputs = entry.get("inputs") or []
        if not isinstance(name, str):
            continue
        signature = _function_signature(name, inputs)
        if Web3.keccak(text=signature).hex()[:8] != selector:
            continue
        arg_types = [str(item.get("type")) for item in inputs if item.get("type")]
        arg_names = [
            str(item.get("name") or f"arg{index}")
            for index, item in enumerate(inputs)
        ]
        decoded_values = abi_decode(arg_types, payload) if arg_types and payload else tuple()
        arguments = tuple(
            DecodedArgument(name=arg_names[index], value=_normalize_value(value), solidity_type=arg_types[index])
            for index, value in enumerate(decoded_values)
        )
        return DecodedFunction(
            selector=selector,
            function_name=name,
            signature=signature,
            arguments=arguments,
            decode_source="verified_abi",
            raw_calldata=raw_calldata,
        )
    return None


def _decode_with_signature(
    *,
    entry: Any,
    signature: str | None,
    selector: str,
    payload: bytes,
) -> tuple[DecodedArgument, ...]:
    if not signature or not payload:
        return ()
    if "(" not in signature:
        return ()
    arg_section = signature[signature.index("(") + 1 : -1]
    if not arg_section:
        return ()
    arg_types = [part.strip() for part in arg_section.split(",")]
    try:
        decoded_values = abi_decode(arg_types, payload)
    except Exception:
        return ()
    return tuple(
        DecodedArgument(
            name=f"arg{index}",
            value=_normalize_value(value),
            solidity_type=arg_type,
        )
        for index, (arg_type, value) in enumerate(zip(arg_types, decoded_values, strict=False))
    )


def _function_signature(name: str, inputs: list[dict[str, Any]]) -> str:
    arg_types = [str(item.get("type")) for item in inputs if item.get("type")]
    return f"{name}({','.join(arg_types)})"


def _normalize_value(value: Any) -> Any:
    if isinstance(value, bytes):
        if len(value) == 32:
            return "0x" + value[-20:].hex()
        return "0x" + value.hex()
    if isinstance(value, (list, tuple)):
        return tuple(_normalize_value(item) for item in value)
    return value
