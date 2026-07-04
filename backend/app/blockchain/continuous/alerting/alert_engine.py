"""Alert generation orchestrator (M10.5)."""

from __future__ import annotations

from datetime import datetime, timezone

from app.blockchain.continuous.alerting.alert_rules import AlertRuleEngine
from app.blockchain.continuous.alerting.deduplicator import AlertDeduplicator
from app.blockchain.continuous.alerting.models import AlertBatch, AlertPolicy, SecurityAlert
from app.blockchain.continuous.alerting.router import AlertRouter
from app.blockchain.continuous.alerting.suppression import AlertSuppressionEngine
from app.blockchain.continuous.risk_delta.models import RiskDeltaReport


class AlertEngine:
    """Generate actionable, deduplicated alerts from risk delta reports."""

    def __init__(
        self,
        rule_engine: AlertRuleEngine | None = None,
        deduplicator: AlertDeduplicator | None = None,
        suppression: AlertSuppressionEngine | None = None,
        router: AlertRouter | None = None,
    ) -> None:
        self._rules = rule_engine or AlertRuleEngine()
        self._deduplicator = deduplicator or AlertDeduplicator()
        self._suppression = suppression or AlertSuppressionEngine()
        self._router = router or AlertRouter()

    def generate(
        self,
        report: RiskDeltaReport,
        *,
        policy: AlertPolicy | None = None,
        recent_alerts: tuple[SecurityAlert, ...] = (),
        generated_at: datetime | None = None,
    ) -> AlertBatch:
        timestamp = generated_at or datetime.now(timezone.utc)
        active_policy = policy or AlertPolicy()

        candidates = self._rules.evaluate(report, generated_at=timestamp)
        unique, batch_duplicates = self._deduplicator.deduplicate_batch(candidates)

        generated, suppressed = self._suppression.apply(
            unique,
            policy=active_policy,
            recent_alerts=recent_alerts,
            now=timestamp,
        )

        duplicate_suppressed = [
            self._suppressed_duplicate(alert, reason="duplicate alert identifier")
            for alert in batch_duplicates
        ]
        all_suppressed = tuple(sorted(suppressed + duplicate_suppressed, key=lambda item: item.alert_id))
        generated_sorted = tuple(sorted(generated, key=lambda item: (item.severity.value, item.alert_id)))
        routing = self._router.route(generated_sorted)

        return AlertBatch(
            watch_id=report.watch_id,
            generated_alerts=generated_sorted,
            suppressed_alerts=all_suppressed,
            routing=routing,
            generated_at=timestamp,
        )

    def acknowledge(self, alert: SecurityAlert) -> SecurityAlert:
        """Mark an alert as acknowledged."""
        return self._suppression.acknowledge(alert)

    def _suppressed_duplicate(self, alert: SecurityAlert, *, reason: str):
        from app.blockchain.continuous.alerting.models import SuppressedAlert

        return SuppressedAlert(
            alert_id=alert.alert_id,
            rule_type=alert.rule_type,
            reason=reason,
            candidate=alert,
        )
