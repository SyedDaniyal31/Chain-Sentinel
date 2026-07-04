"""Deterministic mock risk scoring for development and testing."""

import hashlib
from decimal import Decimal

from app.models.enums import ScanType


def compute_mock_risk_score(scan_type: ScanType, target_address: str) -> Decimal:
    """
    Produce a deterministic mock score in [0.00, 100.00].

    Uses a hash of scan inputs so the same target always yields the same score
    during development — useful for tests and UI demos before real analyzers exist.
    """
    payload = f"{scan_type.value}:{target_address.lower()}".encode()
    digest = hashlib.sha256(payload).hexdigest()
    basis_points = int(digest[:8], 16) % 10_001  # 0..10000
    return Decimal(basis_points) / Decimal(100)
