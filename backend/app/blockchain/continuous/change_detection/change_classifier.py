"""Change severity classification (M10.2)."""

from __future__ import annotations

from app.blockchain.continuous.change_detection.diff_engine import RawChange
from app.blockchain.continuous.change_detection.models import ChangeSeverity, ChangeType
from app.models.enums import ConfidenceLevel

DEFAULT_SEVERITY: dict[ChangeType, ChangeSeverity] = {
    ChangeType.IMPLEMENTATION_CHANGED: ChangeSeverity.CRITICAL,
    ChangeType.OWNER_CHANGED: ChangeSeverity.HIGH,
    ChangeType.PROXY_ADMIN_CHANGED: ChangeSeverity.CRITICAL,
    ChangeType.GOVERNANCE_CHANGED: ChangeSeverity.HIGH,
    ChangeType.LIQUIDITY_CHANGED: ChangeSeverity.MEDIUM,
    ChangeType.TREASURY_CHANGED: ChangeSeverity.HIGH,
    ChangeType.BYTECODE_CHANGED: ChangeSeverity.HIGH,
    ChangeType.DEPENDENCY_CHANGED: ChangeSeverity.MEDIUM,
    ChangeType.RUNTIME_FINGERPRINT_CHANGED: ChangeSeverity.MEDIUM,
}

DEFAULT_CONFIDENCE: dict[ChangeSeverity, ConfidenceLevel] = {
    ChangeSeverity.INFO: ConfidenceLevel.HIGH,
    ChangeSeverity.LOW: ConfidenceLevel.HIGH,
    ChangeSeverity.MEDIUM: ConfidenceLevel.MEDIUM,
    ChangeSeverity.HIGH: ConfidenceLevel.HIGH,
    ChangeSeverity.CRITICAL: ConfidenceLevel.HIGH,
}


class ChangeClassifier:
    """Assign severity and confidence to raw snapshot diffs."""

    def classify(self, change: RawChange) -> tuple[ChangeSeverity, ConfidenceLevel]:
        severity = DEFAULT_SEVERITY.get(change.change_type, ChangeSeverity.INFO)
        confidence = DEFAULT_CONFIDENCE.get(severity, ConfidenceLevel.MEDIUM)
        return severity, confidence
