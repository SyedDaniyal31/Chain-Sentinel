"""Alerting domain models (M10.5)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any

from app.blockchain.risk.evidence_types import EvidenceSeverity


class AlertAcknowledgementState(StrEnum):
    """Acknowledgement lifecycle for a security alert."""

    PENDING = "pending"
    ACKNOWLEDGED = "acknowledged"
    SUPPRESSED = "suppressed"


class AlertRuleType(StrEnum):
    """Rule that generated a security alert."""

    CRITICAL_RISK_INCREASE = "critical_risk_increase"
    HIGH_RISK_INCREASE = "high_risk_increase"
    GOVERNANCE_CHANGE = "governance_change"
    IMPLEMENTATION_CHANGE = "implementation_change"
    OWNERSHIP_CHANGE = "ownership_change"
    TREASURY_CHANGE = "treasury_change"
    RUNTIME_EXPLOIT_INDICATOR = "runtime_exploit_indicator"
    NEW_CRITICAL_EVIDENCE = "new_critical_evidence"


class NotificationChannel(StrEnum):
    """Supported notification channel types."""

    EMAIL = "email"
    SLACK = "slack"
    DISCORD = "discord"
    WEBHOOK = "webhook"
    PAGERDUTY = "pagerduty"
    SIEM = "siem"


@dataclass(frozen=True, slots=True)
class AlertPolicy:
    """Configurable alert generation and suppression policy."""

    minimum_severity: EvidenceSeverity = EvidenceSeverity.MEDIUM
    cooldown_seconds: int = 3600
    suppress_duplicates: bool = True
    respect_acknowledgements: bool = True


@dataclass(frozen=True, slots=True)
class SecurityAlert:
    """Immutable actionable security alert."""

    alert_id: str
    severity: EvidenceSeverity
    title: str
    summary: str
    affected_protocol: str
    affected_contracts: tuple[str, ...]
    evidence_references: tuple[str, ...]
    timestamp: datetime
    acknowledgement_state: AlertAcknowledgementState
    rule_type: AlertRuleType
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class SuppressedAlert:
    """Alert candidate suppressed by policy."""

    alert_id: str
    rule_type: AlertRuleType
    reason: str
    candidate: SecurityAlert


@dataclass(frozen=True, slots=True)
class RoutingDecision:
    """Routing metadata for a generated alert."""

    alert_id: str
    channels: tuple[NotificationChannel, ...]
    priority: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class AlertBatch:
    """Output of alert generation for a risk delta report."""

    watch_id: str
    generated_alerts: tuple[SecurityAlert, ...]
    suppressed_alerts: tuple[SuppressedAlert, ...]
    routing: tuple[RoutingDecision, ...]
    generated_at: datetime
