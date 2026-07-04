"""Continuous monitoring alert engine (M10.5)."""

from app.blockchain.continuous.alerting.alert_engine import AlertEngine
from app.blockchain.continuous.alerting.alert_rules import AlertRuleEngine
from app.blockchain.continuous.alerting.deduplicator import AlertDeduplicator, build_alert_id
from app.blockchain.continuous.alerting.models import (
    AlertAcknowledgementState,
    AlertBatch,
    AlertPolicy,
    AlertRuleType,
    NotificationChannel,
    RoutingDecision,
    SecurityAlert,
    SuppressedAlert,
)
from app.blockchain.continuous.alerting.notification_formatter import NotificationFormatter
from app.blockchain.continuous.alerting.router import (
    AlertRouter,
    DiscordNotificationProvider,
    EmailNotificationProvider,
    NotificationProvider,
    PagerDutyNotificationProvider,
    SiemNotificationProvider,
    SlackNotificationProvider,
    WebhookNotificationProvider,
)
from app.blockchain.continuous.alerting.suppression import AlertSuppressionEngine

__all__ = [
    "AlertAcknowledgementState",
    "AlertBatch",
    "AlertDeduplicator",
    "AlertEngine",
    "AlertPolicy",
    "AlertRouter",
    "AlertRuleEngine",
    "AlertRuleType",
    "AlertSuppressionEngine",
    "DiscordNotificationProvider",
    "EmailNotificationProvider",
    "NotificationChannel",
    "NotificationFormatter",
    "NotificationProvider",
    "PagerDutyNotificationProvider",
    "RoutingDecision",
    "SecurityAlert",
    "SiemNotificationProvider",
    "SlackNotificationProvider",
    "SuppressedAlert",
    "WebhookNotificationProvider",
    "build_alert_id",
]
