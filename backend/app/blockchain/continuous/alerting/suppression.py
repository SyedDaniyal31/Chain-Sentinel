"""Alert suppression policy (M10.5)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.blockchain.continuous.alerting.models import (
    AlertAcknowledgementState,
    AlertPolicy,
    SecurityAlert,
    SuppressedAlert,
)
from app.blockchain.risk.evidence_types import EvidenceSeverity

SEVERITY_ORDER: tuple[EvidenceSeverity, ...] = (
    EvidenceSeverity.INFO,
    EvidenceSeverity.LOW,
    EvidenceSeverity.MEDIUM,
    EvidenceSeverity.HIGH,
    EvidenceSeverity.CRITICAL,
)


class AlertSuppressionEngine:
    """Apply severity, duplicate, cooldown, and acknowledgement suppression."""

    def apply(
        self,
        alerts: list[SecurityAlert],
        *,
        policy: AlertPolicy,
        recent_alerts: tuple[SecurityAlert, ...] = (),
        now: datetime | None = None,
    ) -> tuple[list[SecurityAlert], list[SuppressedAlert]]:
        timestamp = now or datetime.now(timezone.utc)
        recent_index = {item.alert_id: item for item in recent_alerts}
        generated: list[SecurityAlert] = []
        suppressed: list[SuppressedAlert] = []

        for alert in sorted(alerts, key=lambda item: (item.severity.value, item.alert_id)):
            reason = self._suppression_reason(
                alert,
                policy=policy,
                recent_index=recent_index,
                now=timestamp,
            )
            if reason is not None:
                suppressed.append(
                    SuppressedAlert(
                        alert_id=alert.alert_id,
                        rule_type=alert.rule_type,
                        reason=reason,
                        candidate=alert,
                    )
                )
                continue
            generated.append(alert)

        return generated, suppressed

    def acknowledge(self, alert: SecurityAlert) -> SecurityAlert:
        """Return an alert marked as acknowledged."""
        return SecurityAlert(
            alert_id=alert.alert_id,
            severity=alert.severity,
            title=alert.title,
            summary=alert.summary,
            affected_protocol=alert.affected_protocol,
            affected_contracts=alert.affected_contracts,
            evidence_references=alert.evidence_references,
            timestamp=alert.timestamp,
            acknowledgement_state=AlertAcknowledgementState.ACKNOWLEDGED,
            rule_type=alert.rule_type,
            metadata={**alert.metadata, "acknowledged": True},
        )

    def _suppression_reason(
        self,
        alert: SecurityAlert,
        *,
        policy: AlertPolicy,
        recent_index: dict[str, SecurityAlert],
        now: datetime,
    ) -> str | None:
        if not _meets_minimum_severity(alert.severity, policy.minimum_severity):
            return f"below minimum severity threshold ({policy.minimum_severity.value})"

        prior = recent_index.get(alert.alert_id)
        if prior is None:
            return None

        if policy.respect_acknowledgements and prior.acknowledgement_state == AlertAcknowledgementState.ACKNOWLEDGED:
            return "alert acknowledged"

        if policy.cooldown_seconds > 0:
            cooldown_until = prior.timestamp + timedelta(seconds=policy.cooldown_seconds)
            if now < cooldown_until:
                return f"cooldown active until {cooldown_until.isoformat()}"

        return None


def _meets_minimum_severity(current: EvidenceSeverity, minimum: EvidenceSeverity) -> bool:
    return SEVERITY_ORDER.index(current) >= SEVERITY_ORDER.index(minimum)
