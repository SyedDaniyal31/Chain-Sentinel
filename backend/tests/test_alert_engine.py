"""Unit tests for continuous alert engine (M10.5)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app.blockchain.continuous.alerting import (
    AlertAcknowledgementState,
    AlertEngine,
    AlertPolicy,
    AlertRuleType,
    NotificationChannel,
    NotificationFormatter,
)
from app.blockchain.continuous.protocol_subscription import watch_id
from app.blockchain.continuous.reanalysis import DeltaBuilder
from app.blockchain.continuous.risk_delta import RiskDeltaEngine, RiskEvidenceBundle, RiskTrend
from app.blockchain.risk.evidence import create_evidence
from app.blockchain.risk.evidence_types import EvidenceCategory, EvidenceMetadataKey, EvidenceSeverity, EvidenceSource
from app.models.enums import ConfidenceLevel

WATCH = watch_id(1, "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
ROOT = "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
NOW = datetime(2026, 6, 13, 16, 0, tzinfo=timezone.utc)


def _evidence(
    signal: str,
    *,
    source: EvidenceSource = EvidenceSource.GOVERNANCE,
    severity: EvidenceSeverity = EvidenceSeverity.MEDIUM,
    score: str = "10.00",
) -> object:
    return create_evidence(
        source=source,
        category=EvidenceCategory.AUTHORITY,
        signal=signal,
        severity=severity,
        score=Decimal(score),
        confidence=ConfidenceLevel.HIGH,
        reason=f"reason:{signal}",
        metadata={EvidenceMetadataKey.SIGNAL.value: signal},
    )


def _bundle(*evidence: object) -> RiskEvidenceBundle:
    return RiskEvidenceBundle(watch_id=WATCH, evidence=tuple(evidence), captured_at=NOW)


def _report(*, previous: RiskEvidenceBundle, current: RiskEvidenceBundle):
    delta = DeltaBuilder().build(previous.evidence, current.evidence)
    return RiskDeltaEngine().compute(delta, previous, current)


def test_critical_alert_generation() -> None:
    previous = _bundle(_evidence("stable", score="10.00"))
    current = _bundle(
        _evidence("stable", score="10.00"),
        _evidence("implementation_changed", source=EvidenceSource.PROXY, severity=EvidenceSeverity.CRITICAL, score="50.00"),
    )
    report = _report(previous=previous, current=current)
    batch = AlertEngine().generate(report, generated_at=NOW)

    assert report.trend == RiskTrend.INCREASED
    assert batch.generated_alerts
    assert any(alert.rule_type == AlertRuleType.CRITICAL_RISK_INCREASE for alert in batch.generated_alerts)
    assert any(alert.severity == EvidenceSeverity.CRITICAL for alert in batch.generated_alerts)


def test_duplicate_suppression_within_batch() -> None:
    previous = _bundle()
    current = _bundle(
        _evidence("owner_changed", severity=EvidenceSeverity.HIGH, score="25.00"),
    )
    report = _report(previous=previous, current=current)
    candidates = AlertEngine()._rules.evaluate(report, generated_at=NOW)
    duplicate = candidates[0]
    unique, duplicates = AlertEngine()._deduplicator.deduplicate_batch([duplicate, duplicate])

    assert len(unique) == 1
    assert len(duplicates) == 1


def test_cooldown_handling() -> None:
    previous = _bundle()
    current = _bundle(_evidence("owner_changed", score="25.00", severity=EvidenceSeverity.HIGH))
    report = _report(previous=previous, current=current)
    engine = AlertEngine()
    first = engine.generate(report, generated_at=NOW, policy=AlertPolicy(cooldown_seconds=3600))

    second = engine.generate(
        report,
        generated_at=NOW + timedelta(minutes=5),
        recent_alerts=first.generated_alerts,
        policy=AlertPolicy(cooldown_seconds=3600),
    )

    assert first.generated_alerts
    assert second.generated_alerts == ()
    assert any("cooldown active" in item.reason for item in second.suppressed_alerts)


def test_routing_decisions() -> None:
    previous = _bundle()
    current = _bundle(
        _evidence("implementation_changed", source=EvidenceSource.PROXY, severity=EvidenceSeverity.CRITICAL, score="50.00"),
    )
    report = _report(previous=previous, current=current)
    batch = AlertEngine().generate(report, generated_at=NOW)

    assert batch.routing
    decision = batch.routing[0]
    assert NotificationChannel.PAGERDUTY in decision.channels
    assert NotificationChannel.SLACK in decision.channels


def test_deterministic_ordering() -> None:
    previous = _bundle()
    current = _bundle(
        _evidence("owner_changed", score="25.00", severity=EvidenceSeverity.HIGH),
        _evidence("implementation_changed", source=EvidenceSource.PROXY, severity=EvidenceSeverity.CRITICAL, score="50.00"),
    )
    report = _report(previous=previous, current=current)
    engine = AlertEngine()
    batch_one = engine.generate(report, generated_at=NOW)
    batch_two = engine.generate(report, generated_at=NOW)

    assert [item.alert_id for item in batch_one.generated_alerts] == [
        item.alert_id for item in batch_two.generated_alerts
    ]


def test_acknowledgement_handling() -> None:
    previous = _bundle()
    current = _bundle(_evidence("owner_changed", score="25.00", severity=EvidenceSeverity.HIGH))
    report = _report(previous=previous, current=current)
    engine = AlertEngine()
    batch = engine.generate(report, generated_at=NOW)
    acknowledged = tuple(engine.acknowledge(alert) for alert in batch.generated_alerts)

    assert all(item.acknowledgement_state == AlertAcknowledgementState.ACKNOWLEDGED for item in acknowledged)

    follow_up = engine.generate(
        report,
        generated_at=NOW + timedelta(hours=2),
        recent_alerts=acknowledged,
        policy=AlertPolicy(cooldown_seconds=60, respect_acknowledgements=True),
    )

    assert follow_up.generated_alerts == ()
    assert any(item.reason == "alert acknowledged" for item in follow_up.suppressed_alerts)


def test_notification_formatter() -> None:
    previous = _bundle()
    current = _bundle(_evidence("owner_changed", score="25.00", severity=EvidenceSeverity.HIGH))
    report = _report(previous=previous, current=current)
    batch = AlertEngine().generate(report, generated_at=NOW)
    formatter = NotificationFormatter()
    payload = formatter.format(batch.generated_alerts[0], channel=NotificationChannel.EMAIL)

    assert payload["subject"].startswith("[HIGH]")
    assert ROOT in payload["contracts"]
