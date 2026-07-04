"""Alert notification formatting (M10.5)."""

from __future__ import annotations

from typing import Any

from app.blockchain.continuous.alerting.models import NotificationChannel, RoutingDecision, SecurityAlert


class NotificationFormatter:
    """Format security alerts for downstream notification providers."""

    def format(self, alert: SecurityAlert, *, channel: NotificationChannel) -> dict[str, Any]:
        payload = {
            "alert_id": alert.alert_id,
            "severity": alert.severity.value,
            "title": alert.title,
            "summary": alert.summary,
            "protocol": alert.affected_protocol,
            "contracts": list(alert.affected_contracts),
            "evidence_references": list(alert.evidence_references),
            "timestamp": alert.timestamp.isoformat(),
            "rule_type": alert.rule_type.value,
            "acknowledgement_state": alert.acknowledgement_state.value,
            "metadata": alert.metadata,
        }
        if channel == NotificationChannel.SLACK:
            payload["text"] = self._slack_text(alert)
        elif channel == NotificationChannel.EMAIL:
            payload["subject"] = f"[{alert.severity.value.upper()}] {alert.title}"
            payload["body"] = self._plain_text(alert)
        elif channel == NotificationChannel.PAGERDUTY:
            payload["summary"] = alert.title
            payload["source"] = "chainsentinel"
        return payload

    def format_batch(
        self,
        alerts: tuple[SecurityAlert, ...],
        routing: tuple[RoutingDecision, ...],
    ) -> dict[str, list[dict[str, Any]]]:
        route_index = {item.alert_id: item for item in routing}
        grouped: dict[str, list[dict[str, Any]]] = {}
        for alert in alerts:
            decision = route_index.get(alert.alert_id)
            channels = decision.channels if decision else (NotificationChannel.WEBHOOK,)
            for channel in channels:
                grouped.setdefault(channel.value, []).append(self.format(alert, channel=channel))
        return grouped

    def _plain_text(self, alert: SecurityAlert) -> str:
        contracts = ", ".join(alert.affected_contracts) or "n/a"
        evidence = ", ".join(alert.evidence_references) or "n/a"
        return (
            f"{alert.title}\n\n"
            f"{alert.summary}\n\n"
            f"Protocol: {alert.affected_protocol}\n"
            f"Contracts: {contracts}\n"
            f"Evidence: {evidence}\n"
            f"Severity: {alert.severity.value}\n"
        )

    def _slack_text(self, alert: SecurityAlert) -> str:
        return f"*{alert.title}* — {alert.summary} (`{alert.severity.value}`)"
