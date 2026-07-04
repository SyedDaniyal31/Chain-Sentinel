"""Evidence indexing helpers for correlation matching (M7.2)."""

from __future__ import annotations

from collections.abc import Sequence

from app.blockchain.risk.evidence_types import EvidenceMetadataKey
from app.blockchain.risk.models import RiskEvidence
from app.models.enums import ConfidenceLevel


class EvidenceIndex:
    """Deterministic lookup structure for correlation rule evaluation."""

    def __init__(self, evidence: Sequence[RiskEvidence]) -> None:
        self._evidence = tuple(evidence)
        self._by_id = {item.id: item for item in self._evidence}
        self._by_signal: dict[str, tuple[RiskEvidence, ...]] = {}
        signal_key = EvidenceMetadataKey.SIGNAL.value
        for item in self._evidence:
            signal = item.metadata.get(signal_key)
            if isinstance(signal, str):
                self._by_signal.setdefault(signal, ())
                self._by_signal[signal] = self._by_signal[signal] + (item,)

    @property
    def evidence(self) -> tuple[RiskEvidence, ...]:
        return self._evidence

    def get(self, evidence_id: str) -> RiskEvidence | None:
        return self._by_id.get(evidence_id)

    def has_signal(self, signal: str) -> bool:
        return signal in self._by_signal

    def items_with_signal(self, signal: str) -> tuple[RiskEvidence, ...]:
        return self._by_signal.get(signal, ())

    def has_any_signal(self, *signals: str) -> bool:
        return any(self.has_signal(signal) for signal in signals)

    def has_signal_prefix(self, prefix: str) -> bool:
        return any(signal.startswith(prefix) for signal in self._by_signal)

    def has_admin_eoa_without_timelock(self) -> bool:
        admin_items = self.items_with_signal("admin_address")
        if not admin_items:
            return False
        if self.has_signal("has_timelock"):
            return False
        for item in admin_items:
            if item.metadata.get(EvidenceMetadataKey.IS_TIMELOCK.value):
                return False
            admin_type = item.metadata.get(EvidenceMetadataKey.ADMIN_TYPE.value)
            owner_type = item.metadata.get(EvidenceMetadataKey.OWNER_TYPE.value)
            effective = owner_type if owner_type is not None else admin_type
            if effective in {None, "eoa"}:
                return True
        return False

    def has_upgrade_authority(self) -> bool:
        return self.has_signal("admin_address") or self.has_signal("is_upgradeable")

    def has_admin_capability(self) -> bool:
        return self.has_any_signal(
            "mint_capability",
            "pause_capability",
            "blacklist_capability",
            "ownership_capability",
        )

    def has_low_wallet_reputation(self) -> bool:
        return self.has_any_signal("wallet_known_scam", "tornado_funded_deployer")

    @staticmethod
    def aggregate_confidence(items: Sequence[RiskEvidence]) -> ConfidenceLevel:
        """Propagate confidence as the minimum confidence among matched evidence."""
        if not items:
            return ConfidenceLevel.LOW
        order = {
            ConfidenceLevel.LOW: 0,
            ConfidenceLevel.MEDIUM: 1,
            ConfidenceLevel.HIGH: 2,
        }
        return min(items, key=lambda item: order[item.confidence]).confidence
