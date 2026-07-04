"""Unit tests for risk delta engine (M10.4)."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from app.blockchain.continuous.protocol_subscription import watch_id
from app.blockchain.continuous.reanalysis import DeltaBuilder
from app.blockchain.continuous.reanalysis.models import EvidenceDelta
from app.blockchain.continuous.risk_delta import (
    RiskDeltaEngine,
    RiskEvidenceBundle,
    RiskTrend,
)
from app.blockchain.risk.evidence import create_evidence
from app.blockchain.risk.evidence_types import EvidenceCategory, EvidenceMetadataKey, EvidenceSeverity, EvidenceSource
from app.models.enums import ConfidenceLevel

WATCH = watch_id(1, "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
NOW = datetime(2026, 6, 13, 15, 0, tzinfo=timezone.utc)


def _evidence(
    signal: str,
    *,
    source: EvidenceSource = EvidenceSource.GOVERNANCE,
    category: EvidenceCategory = EvidenceCategory.AUTHORITY,
    severity: EvidenceSeverity = EvidenceSeverity.MEDIUM,
    score: str = "10.00",
    reason_only: bool = False,
) -> object:
    metadata = {EvidenceMetadataKey.SIGNAL.value: signal}
    if reason_only:
        metadata[EvidenceMetadataKey.REASON_ONLY.value] = True
    return create_evidence(
        source=source,
        category=category,
        signal=signal,
        severity=severity,
        score=Decimal(score),
        confidence=ConfidenceLevel.HIGH,
        reason=f"reason:{signal}",
        metadata=metadata,
    )


def _bundle(*evidence: object) -> RiskEvidenceBundle:
    return RiskEvidenceBundle(
        watch_id=WATCH,
        evidence=tuple(evidence),
        captured_at=NOW,
    )


def _delta(previous: RiskEvidenceBundle, current: RiskEvidenceBundle) -> EvidenceDelta:
    return DeltaBuilder().build(previous.evidence, current.evidence)


def test_risk_increase() -> None:
    previous = _bundle(_evidence("stable", score="10.00"))
    current = _bundle(
        _evidence("stable", score="10.00"),
        _evidence("new_risk", score="25.00", severity=EvidenceSeverity.HIGH),
    )
    report = RiskDeltaEngine().compute(_delta(previous, current), previous, current)

    assert report.trend == RiskTrend.INCREASED
    assert report.delta.score_delta == Decimal("25.00")
    assert report.current_summary.total_score == Decimal("35.00")


def test_risk_decrease() -> None:
    previous = _bundle(
        _evidence("stable", score="10.00"),
        _evidence("old_risk", score="30.00", severity=EvidenceSeverity.HIGH),
    )
    current = _bundle(_evidence("stable", score="10.00"))
    report = RiskDeltaEngine().compute(_delta(previous, current), previous, current)

    assert report.trend == RiskTrend.DECREASED
    assert report.delta.score_delta == Decimal("-30.00")
    assert report.current_summary.total_score == Decimal("10.00")


def test_unchanged_risk() -> None:
    previous = _bundle(_evidence("stable", score="10.00"))
    current = _bundle(_evidence("stable", score="10.00"))
    report = RiskDeltaEngine().compute(_delta(previous, current), previous, current)

    assert report.trend == RiskTrend.UNCHANGED
    assert report.delta.score_delta == Decimal("0.00")
    assert report.explanation.reasons == ("No material risk evidence changes detected",)


def test_added_evidence_summary() -> None:
    previous = _bundle()
    current = _bundle(_evidence("mint_capability", source=EvidenceSource.CAPABILITY, score="20.00"))
    report = RiskDeltaEngine().compute(_delta(previous, current), previous, current)

    assert report.evidence_summary.added_count == 1
    assert "mint_capability" in report.evidence_summary.contributing_signals
    assert "capability" in report.evidence_summary.affected_domains


def test_removed_evidence_summary() -> None:
    previous = _bundle(_evidence("unlocked_lp", source=EvidenceSource.LIQUIDITY, score="15.00"))
    current = _bundle()
    report = RiskDeltaEngine().compute(_delta(previous, current), previous, current)

    assert report.evidence_summary.removed_count == 1
    assert report.trend == RiskTrend.DECREASED
    assert "liquidity" in report.explanation.affected_domains


def test_updated_evidence() -> None:
    previous = _bundle(_evidence("admin_authority", score="10.00"))
    current = _bundle(_evidence("admin_authority", score="35.00", severity=EvidenceSeverity.HIGH))
    report = RiskDeltaEngine().compute(_delta(previous, current), previous, current)

    assert report.evidence_summary.updated_count == 1
    assert report.trend == RiskTrend.INCREASED
    assert any("Updated governance evidence" in reason for reason in report.explanation.reasons)


def test_deterministic_explanations() -> None:
    previous = _bundle(_evidence("baseline", score="5.00"))
    current = _bundle(
        _evidence("baseline", score="5.00"),
        _evidence(
            "threat_surface",
            source=EvidenceSource.THREAT_SURFACE,
            category=EvidenceCategory.THREAT,
            score="40.00",
            severity=EvidenceSeverity.HIGH,
        ),
    )
    engine = RiskDeltaEngine()
    delta = _delta(previous, current)

    report_one = engine.compute(delta, previous, current)
    report_two = engine.compute(delta, previous, current)

    assert report_one.explanation.headline == report_two.explanation.headline
    assert report_one.explanation.reasons == report_two.explanation.reasons
    assert report_one.explanation.contributing_evidence_ids == report_two.explanation.contributing_evidence_ids
    assert report_one.evidence_summary == report_two.evidence_summary


def test_reason_only_evidence_does_not_affect_score() -> None:
    previous = _bundle()
    current = _bundle(_evidence("observation", score="99.00", reason_only=True))
    report = RiskDeltaEngine().compute(_delta(previous, current), previous, current)

    assert report.current_summary.total_score == Decimal("0.00")
    assert report.trend == RiskTrend.UNCHANGED
