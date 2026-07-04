"""Approval and allowance detection (M9.1)."""

from __future__ import annotations

from app.blockchain.runtime.transaction.models import ApprovalFinding, ApprovalKind, DecodedFunction, TransactionMetadata

MAX_UINT256 = (1 << 256) - 1
LARGE_ALLOWANCE_THRESHOLD = 10**30


class ApprovalAnalyzer:
    """Detect approve(), permit(), and setApprovalForAll() operations."""

    APPROVE = "095ea7b3"
    PERMIT = "d505accf"
    SET_APPROVAL_FOR_ALL = "a22cb465"

    @classmethod
    def analyze(
        cls,
        metadata: TransactionMetadata,
        decoded_function: DecodedFunction | None,
    ) -> tuple[ApprovalFinding, ...]:
        if decoded_function is None or metadata.to_address is None:
            return ()

        selector = decoded_function.selector
        if selector == cls.APPROVE and len(decoded_function.arguments) >= 2:
            return (
                cls._build_allowance_finding(
                    kind=ApprovalKind.APPROVE,
                    metadata=metadata,
                    spender=str(decoded_function.arguments[0].value),
                    amount=_coerce_int(decoded_function.arguments[1].value),
                ),
            )
        if selector == cls.PERMIT and len(decoded_function.arguments) >= 3:
            return (
                cls._build_allowance_finding(
                    kind=ApprovalKind.PERMIT,
                    metadata=metadata,
                    spender=str(decoded_function.arguments[1].value),
                    amount=_coerce_int(decoded_function.arguments[2].value),
                ),
            )
        if selector == cls.SET_APPROVAL_FOR_ALL and len(decoded_function.arguments) >= 2:
            approved = bool(decoded_function.arguments[1].value)
            if not approved:
                return ()
            return (
                ApprovalFinding(
                    kind=ApprovalKind.SET_APPROVAL_FOR_ALL,
                    token_address=metadata.to_address,
                    owner_address=metadata.from_address,
                    spender_address=str(decoded_function.arguments[0].value),
                    amount=None,
                    is_unlimited=True,
                    is_infinite_allowance=True,
                    spender_risk_indicators=cls._spender_risk_indicators(
                        str(decoded_function.arguments[0].value),
                        unlimited=True,
                    ),
                ),
            )
        return ()

    @classmethod
    def _build_allowance_finding(
        cls,
        *,
        kind: ApprovalKind,
        metadata: TransactionMetadata,
        spender: str,
        amount: int,
    ) -> ApprovalFinding:
        is_unlimited = amount >= MAX_UINT256 or amount >= LARGE_ALLOWANCE_THRESHOLD
        return ApprovalFinding(
            kind=kind,
            token_address=metadata.to_address or "",
            owner_address=metadata.from_address,
            spender_address=spender,
            amount=amount,
            is_unlimited=is_unlimited,
            is_infinite_allowance=amount >= MAX_UINT256,
            spender_risk_indicators=cls._spender_risk_indicators(spender, unlimited=is_unlimited),
        )

    @staticmethod
    def _spender_risk_indicators(spender: str, *, unlimited: bool) -> tuple[str, ...]:
        indicators: list[str] = []
        if unlimited:
            indicators.append("unlimited_allowance")
        if spender.lower() in {
            "0x0000000000000000000000000000000000000000",
            "0x000000000000000000000000000000000000dead",
        }:
            indicators.append("burn_or_null_spender")
        if spender.lower().startswith("0x"):
            indicators.append("external_spender")
        return tuple(sorted(set(indicators)))


def _coerce_int(value: object) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.startswith("0x"):
        return int(value, 16)
    return int(value)
