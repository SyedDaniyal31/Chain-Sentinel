"""Alert routing and notification provider interfaces (M10.5)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.blockchain.continuous.alerting.models import NotificationChannel, RoutingDecision, SecurityAlert
from app.blockchain.risk.evidence_types import EvidenceSeverity


class NotificationProvider(ABC):
    """Future integration point for external notification backends."""

    channel: NotificationChannel

    @abstractmethod
    async def send(self, payload: dict[str, Any]) -> None:
        """Deliver a formatted alert payload to the provider."""


class EmailNotificationProvider(NotificationProvider):
    channel = NotificationChannel.EMAIL

    async def send(self, payload: dict[str, Any]) -> None:
        raise NotImplementedError("email provider not implemented in M10.5")


class SlackNotificationProvider(NotificationProvider):
    channel = NotificationChannel.SLACK

    async def send(self, payload: dict[str, Any]) -> None:
        raise NotImplementedError("slack provider not implemented in M10.5")


class DiscordNotificationProvider(NotificationProvider):
    channel = NotificationChannel.DISCORD

    async def send(self, payload: dict[str, Any]) -> None:
        raise NotImplementedError("discord provider not implemented in M10.5")


class WebhookNotificationProvider(NotificationProvider):
    channel = NotificationChannel.WEBHOOK

    async def send(self, payload: dict[str, Any]) -> None:
        raise NotImplementedError("webhook provider not implemented in M10.5")


class PagerDutyNotificationProvider(NotificationProvider):
    channel = NotificationChannel.PAGERDUTY

    async def send(self, payload: dict[str, Any]) -> None:
        raise NotImplementedError("pagerduty provider not implemented in M10.5")


class SiemNotificationProvider(NotificationProvider):
    channel = NotificationChannel.SIEM

    async def send(self, payload: dict[str, Any]) -> None:
        raise NotImplementedError("siem provider not implemented in M10.5")


class AlertRouter:
    """Determine routing metadata for generated alerts."""

    CRITICAL_CHANNELS: tuple[NotificationChannel, ...] = (
        NotificationChannel.PAGERDUTY,
        NotificationChannel.SLACK,
        NotificationChannel.EMAIL,
        NotificationChannel.SIEM,
    )
    HIGH_CHANNELS: tuple[NotificationChannel, ...] = (
        NotificationChannel.SLACK,
        NotificationChannel.EMAIL,
        NotificationChannel.WEBHOOK,
    )
    DEFAULT_CHANNELS: tuple[NotificationChannel, ...] = (
        NotificationChannel.WEBHOOK,
        NotificationChannel.EMAIL,
    )

    def route(self, alerts: tuple[SecurityAlert, ...]) -> tuple[RoutingDecision, ...]:
        decisions: list[RoutingDecision] = []
        for alert in sorted(alerts, key=lambda item: (item.severity.value, item.alert_id)):
            channels = self._channels_for_severity(alert.severity)
            decisions.append(
                RoutingDecision(
                    alert_id=alert.alert_id,
                    channels=channels,
                    priority=alert.severity.value,
                    metadata={
                        "rule_type": alert.rule_type.value,
                        "affected_protocol": alert.affected_protocol,
                    },
                )
            )
        return tuple(decisions)

    def _channels_for_severity(self, severity: EvidenceSeverity) -> tuple[NotificationChannel, ...]:
        if severity == EvidenceSeverity.CRITICAL:
            return self.CRITICAL_CHANNELS
        if severity == EvidenceSeverity.HIGH:
            return self.HIGH_CHANNELS
        return self.DEFAULT_CHANNELS
