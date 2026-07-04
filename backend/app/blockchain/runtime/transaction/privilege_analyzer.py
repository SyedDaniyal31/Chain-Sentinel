"""Privileged administrative operation detection (M9.1)."""

from __future__ import annotations

from app.blockchain.runtime.transaction.models import (
    DecodedFunction,
    PrivilegedAction,
    PrivilegedOperation,
    TransactionMetadata,
)

LARGE_VALUE_THRESHOLD = 10**21


class PrivilegeAnalyzer:
    """Detect upgrade, pause, mint, burn, ownership, and role operations."""

    SELECTOR_TO_OPERATION: dict[str, PrivilegedOperation] = {
        "3659cfe6": PrivilegedOperation.UPGRADE_TO,
        "4f1ef286": PrivilegedOperation.UPGRADE_TO_AND_CALL,
        "9ded06df": PrivilegedOperation.SET_IMPLEMENTATION,
        "8456cb59": PrivilegedOperation.PAUSE,
        "3f4ba83a": PrivilegedOperation.UNPAUSE,
        "40c10f19": PrivilegedOperation.MINT,
        "a0712d68": PrivilegedOperation.MINT,
        "42966c68": PrivilegedOperation.BURN,
        "79cc6790": PrivilegedOperation.BURN,
        "f2fde38b": PrivilegedOperation.TRANSFER_OWNERSHIP,
        "2f2ff15d": PrivilegedOperation.GRANT_ROLE,
        "d547741f": PrivilegedOperation.REVOKE_ROLE,
    }

    @classmethod
    def analyze(
        cls,
        metadata: TransactionMetadata,
        decoded_function: DecodedFunction | None,
    ) -> tuple[PrivilegedAction, ...]:
        if decoded_function is None or metadata.to_address is None:
            return ()

        operation = cls.SELECTOR_TO_OPERATION.get(decoded_function.selector)
        if operation is None:
            operation = _operation_from_name(decoded_function.function_name)
        if operation is None:
            return ()

        target_address = _extract_target(decoded_function)
        role = _extract_role(decoded_function)
        amount = _extract_amount(decoded_function)
        is_large = bool(
            (amount is not None and amount >= LARGE_VALUE_THRESHOLD)
            or metadata.value_wei >= LARGE_VALUE_THRESHOLD
        )

        return (
            PrivilegedAction(
                operation=operation,
                contract_address=metadata.to_address,
                actor_address=metadata.from_address,
                target_address=target_address,
                role=role,
                amount=amount,
                is_large_transfer=is_large,
            ),
        )


def _operation_from_name(function_name: str) -> PrivilegedOperation | None:
    normalized = function_name.lower()
    mapping = {
        "upgradeto": PrivilegedOperation.UPGRADE_TO,
        "upgradetoandcall": PrivilegedOperation.UPGRADE_TO_AND_CALL,
        "setimplementation": PrivilegedOperation.SET_IMPLEMENTATION,
        "pause": PrivilegedOperation.PAUSE,
        "unpause": PrivilegedOperation.UNPAUSE,
        "mint": PrivilegedOperation.MINT,
        "burn": PrivilegedOperation.BURN,
        "burnfrom": PrivilegedOperation.BURN,
        "transferownership": PrivilegedOperation.TRANSFER_OWNERSHIP,
        "grantrole": PrivilegedOperation.GRANT_ROLE,
        "revokerole": PrivilegedOperation.REVOKE_ROLE,
    }
    return mapping.get(normalized)


def _extract_target(decoded_function: DecodedFunction) -> str | None:
    if not decoded_function.arguments:
        return None
    first = decoded_function.arguments[0].value
    if isinstance(first, str) and first.startswith("0x"):
        return first.lower()
    return None


def _extract_role(decoded_function: DecodedFunction) -> str | None:
    if decoded_function.function_name.lower() not in {"grantrole", "revokerole"}:
        return None
    if not decoded_function.arguments:
        return None
    role = decoded_function.arguments[0].value
    if isinstance(role, str):
        return role
    if isinstance(role, bytes):
        return "0x" + role.hex()
    return str(role)


def _extract_amount(decoded_function: DecodedFunction) -> int | None:
    if decoded_function.function_name.lower() in {"mint", "burn"}:
        for argument in decoded_function.arguments:
            if argument.solidity_type.startswith("uint") and isinstance(argument.value, int):
                return argument.value
    if decoded_function.function_name.lower() == "mint" and len(decoded_function.arguments) >= 2:
        return _coerce_int(decoded_function.arguments[1].value)
    return None


def _coerce_int(value: object) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.startswith("0x"):
        return int(value, 16)
    return int(value)
