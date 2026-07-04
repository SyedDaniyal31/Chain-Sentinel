"""Runtime call frame classification (M9.2)."""

from __future__ import annotations

from app.blockchain.runtime.calltrace.models import (
    CallClassification,
    CallType,
    RawTraceNode,
)


class CallClassifier:
    """Assign semantic classifications to runtime call frames."""

    def classify(
        self,
        frame: RawTraceNode,
        *,
        depth: int,
        parent_id: str | None,
    ) -> CallClassification:
        if frame.call_type in {CallType.CREATE, CallType.CREATE2}:
            return CallClassification.CREATION
        if frame.call_type == CallType.SELFDESTRUCT:
            return CallClassification.DESTRUCTION
        if frame.call_type == CallType.DELEGATECALL:
            return CallClassification.DELEGATE
        if frame.call_type == CallType.STATICCALL:
            return CallClassification.STATIC
        if depth == 0:
            return CallClassification.TOP_LEVEL
        if frame.value_wei > 0 and len(frame.input) == 0:
            return CallClassification.VALUE_TRANSFER
        if parent_id is None:
            return CallClassification.EXTERNAL
        if depth == 1:
            return CallClassification.EXTERNAL
        return CallClassification.INTERNAL
