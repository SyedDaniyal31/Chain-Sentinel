"""Alert deduplication utilities (M10.5)."""

from __future__ import annotations

import hashlib

from app.blockchain.continuous.alerting.models import AlertRuleType, SecurityAlert


def build_alert_id(
    *,
    watch_id: str,
    rule_type: AlertRuleType,
    evidence_ids: tuple[str, ...],
) -> str:
    """Build a stable alert identifier for deduplication."""
    fingerprint = "|".join(
        [
            watch_id,
            rule_type.value,
            ",".join(sorted(evidence_ids)),
        ]
    )
    digest = hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()[:16]
    return f"{watch_id}:alert:{rule_type.value}:{digest}"


class AlertDeduplicator:
    """Prevent duplicate alerts within a batch and against recent history."""

    def deduplicate_batch(self, candidates: list[SecurityAlert]) -> tuple[list[SecurityAlert], list[SecurityAlert]]:
        """Return unique alerts and duplicates suppressed within the batch."""
        unique: list[SecurityAlert] = []
        duplicates: list[SecurityAlert] = []
        seen: set[str] = set()
        for alert in sorted(candidates, key=_alert_sort_key):
            if alert.alert_id in seen:
                duplicates.append(alert)
                continue
            seen.add(alert.alert_id)
            unique.append(alert)
        return unique, duplicates

    def filter_recent(
        self,
        alerts: list[SecurityAlert],
        *,
        recent_alert_ids: set[str],
    ) -> tuple[list[SecurityAlert], list[SecurityAlert]]:
        """Split alerts into new items and those already seen recently."""
        fresh: list[SecurityAlert] = []
        recent: list[SecurityAlert] = []
        for alert in alerts:
            if alert.alert_id in recent_alert_ids:
                recent.append(alert)
            else:
                fresh.append(alert)
        return fresh, recent


def _alert_sort_key(alert: SecurityAlert) -> tuple[str, str, str]:
    return (alert.severity.value, alert.rule_type.value, alert.alert_id)
