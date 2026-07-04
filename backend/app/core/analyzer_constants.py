"""Analyzer versioning and detection-method resolution."""

from app.models.enums import (
    CapabilityDetectionMethod,
    HoneypotDetectionMethod,
    ScanDetectionMethod,
)

ANALYZER_VERSION = "1.1.0"


def resolve_scan_detection_method(
    capability_method: CapabilityDetectionMethod,
    honeypot_method: HoneypotDetectionMethod,
) -> ScanDetectionMethod | None:
    """
    Merge capability and honeypot detection paths into a persisted scan-level method.

    Returns hybrid when more than one distinct technique contributed.
    """
    tags: set[str] = set()

    if capability_method == CapabilityDetectionMethod.SOURCE:
        tags.add(ScanDetectionMethod.SOURCE.value)
    elif capability_method == CapabilityDetectionMethod.BYTECODE:
        tags.add(ScanDetectionMethod.BYTECODE.value)

    if honeypot_method == HoneypotDetectionMethod.SIMULATION:
        tags.add(ScanDetectionMethod.SIMULATION.value)
    elif honeypot_method == HoneypotDetectionMethod.SOURCE:
        tags.add(ScanDetectionMethod.SOURCE.value)
    elif honeypot_method == HoneypotDetectionMethod.BYTECODE:
        tags.add(ScanDetectionMethod.BYTECODE.value)

    if not tags:
        return None
    if len(tags) > 1:
        return ScanDetectionMethod.HYBRID
    return ScanDetectionMethod(next(iter(tags)))
