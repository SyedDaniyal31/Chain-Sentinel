"""Unit tests for baseline history and timeline (M10.6)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app.blockchain.continuous.alerting import AlertAcknowledgementState, AlertEngine, AlertRuleType
from app.blockchain.continuous.change_detection import SnapshotBuilder
from app.blockchain.continuous.change_detection.models import (
    ChangeDetectionResult,
    ChangeEvent,
    ChangeSeverity,
    ChangeType,
)
from app.blockchain.continuous.history import (
    HistoryIngestor,
    HistoryRecordType,
    InMemoryBaselineStore,
    InMemoryHistoryStore,
    RetentionEngine,
    RetentionPolicy,
    SnapshotArchiver,
    TimelineBuilder,
    TrendAnalyzer,
    dump_baseline_store,
    dump_history_store,
    load_baseline_store,
    load_history_store,
)
from app.blockchain.continuous.protocol_subscription import watch_id
from app.blockchain.continuous.reanalysis import DeltaBuilder
from app.blockchain.continuous.reanalysis.models import (
    EvidenceDelta,
    ExecutionPlan,
    ReanalysisMetrics,
    ReanalysisModule,
    ReanalysisResult,
)
from app.blockchain.continuous.risk_delta import RiskDeltaEngine, RiskEvidenceBundle, RiskTrend
from app.blockchain.risk.evidence import create_evidence
from app.blockchain.risk.evidence_types import EvidenceCategory, EvidenceMetadataKey, EvidenceSeverity, EvidenceSource
from app.models.enums import ConfidenceLevel

ROOT = "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
PROXY = "0xcccccccccccccccccccccccccccccccccccccccc"
WATCH = watch_id(1, ROOT)
T0 = datetime(2026, 6, 13, 12, 0, tzinfo=timezone.utc)
T1 = datetime(2026, 6, 13, 13, 0, tzinfo=timezone.utc)
T2 = datetime(2026, 6, 13, 14, 0, tzinfo=timezone.utc)
T3 = datetime(2026, 6, 13, 15, 0, tzinfo=timezone.utc)


def _snapshot(*, captured_at: datetime, suffix: str) -> object:
    return SnapshotBuilder().build(
        {
            "watch_id": WATCH,
            "chain_id": 1,
            "root_address": ROOT,
            "captured_at": captured_at,
            "snapshot_id": f"{WATCH}:{suffix}",
            "dependency_fingerprint": "deps:v1",
            "liquidity_fingerprint": "liquidity:v1",
            "runtime_fingerprint": "runtime:v1",
            "contracts": [
                {
                    "address": PROXY,
                    "proxy_implementation": "0xdddddddddddddddddddddddddddddddddddddddd",
                    "owner": ROOT,
                    "bytecode_hash": f"bytecode:{suffix}",
                    "abi_hash": f"abi:{suffix}",
                }
            ],
        },
        captured_at=captured_at,
    )


def _change(change_type: ChangeType, *, timestamp: datetime = T1) -> ChangeEvent:
    return ChangeEvent(
        event_id=f"{WATCH}:{change_type.value}:test",
        change_type=change_type,
        severity=ChangeSeverity.HIGH,
        before="before",
        after="after",
        affected_contracts=(PROXY,),
        timestamp=timestamp,
        confidence=ConfidenceLevel.HIGH,
    )


def _change_result(
    *,
    changes: tuple[ChangeEvent, ...],
    detected_at: datetime = T1,
    unchanged: bool = False,
) -> ChangeDetectionResult:
    return ChangeDetectionResult(
        watch_id=WATCH,
        baseline_snapshot_id=f"{WATCH}:baseline",
        current_snapshot_id=f"{WATCH}:current",
        detected_at=detected_at,
        changes=changes,
        unchanged=unchanged,
    )


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


def _bundle(*evidence: object, captured_at: datetime) -> RiskEvidenceBundle:
    return RiskEvidenceBundle(watch_id=WATCH, evidence=tuple(evidence), captured_at=captured_at)


def _risk_report(*, previous: RiskEvidenceBundle, current: RiskEvidenceBundle):
    delta = DeltaBuilder().build(previous.evidence, current.evidence)
    return RiskDeltaEngine().compute(delta, previous, current)


def _reanalysis_result(*, changes: tuple[ChangeEvent, ...], detected_at: datetime = T1) -> ReanalysisResult:
    change_result = _change_result(changes=changes, detected_at=detected_at, unchanged=len(changes) == 0)
    return ReanalysisResult(
        watch_id=WATCH,
        execution_plan=ExecutionPlan(
            plan_id=f"{WATCH}:plan:{detected_at.isoformat()}",
            watch_id=WATCH,
            modules=(ReanalysisModule.GOVERNANCE,),
            triggered_by=tuple(item.change_type for item in changes),
            affected_contracts=(PROXY,),
        ),
        executed_modules=(ReanalysisModule.GOVERNANCE,),
        new_evidence=(),
        evidence_delta=EvidenceDelta(added=(), removed=(), updated=()),
        metrics=ReanalysisMetrics(
            modules_planned=1,
            modules_executed=1,
            duration_ms=12.5,
            evidence_added_count=0,
            evidence_removed_count=0,
            evidence_updated_count=0,
        ),
        change_result=change_result,
    )


def _ingest_cycle(
    store: InMemoryHistoryStore,
    *,
    captured_at: datetime,
    suffix: str,
    changes: tuple[ChangeEvent, ...] = (),
    risk_previous: RiskEvidenceBundle | None = None,
    risk_current: RiskEvidenceBundle | None = None,
) -> None:
    ingestor = HistoryIngestor()
    snapshot = _snapshot(captured_at=captured_at, suffix=suffix)
    store.append(ingestor.ingest_snapshot(snapshot))

    change_result = _change_result(changes=changes, detected_at=captured_at, unchanged=len(changes) == 0)
    store.append(ingestor.ingest_change_result(change_result))

    reanalysis = _reanalysis_result(changes=changes, detected_at=captured_at)
    store.append(ingestor.ingest_reanalysis_result(reanalysis))
    store.append(ingestor.ingest_evidence_delta(reanalysis))

    if risk_previous is not None and risk_current is not None:
        report = _risk_report(previous=risk_previous, current=risk_current)
        store.append(ingestor.ingest_risk_delta(report, captured_at=captured_at))
        batch = AlertEngine().generate(report, generated_at=captured_at)
        for record in ingestor.ingest_alert_batch(batch):
            store.append(record)


def test_history_persistence_round_trip() -> None:
    baseline_store = InMemoryBaselineStore()
    history_store = InMemoryHistoryStore()
    archiver = SnapshotArchiver(baseline_store=baseline_store, history_store=history_store)

    snapshot = _snapshot(captured_at=T0, suffix="baseline")
    archiver.archive(snapshot, as_baseline=True)
    _ingest_cycle(
        history_store,
        captured_at=T1,
        suffix="cycle-1",
        changes=(_change(ChangeType.OWNER_CHANGED, timestamp=T1),),
        risk_previous=_bundle(captured_at=T0),
        risk_current=_bundle(_evidence("owner_changed", severity=EvidenceSeverity.HIGH, score="25.00"), captured_at=T1),
    )

    restored_baseline = load_baseline_store(dump_baseline_store(baseline_store))
    restored_history = load_history_store(dump_history_store(history_store))

    assert restored_baseline.has_baseline(WATCH)
    assert len(restored_history.list_records(WATCH)) == len(history_store.list_records(WATCH))


def test_timeline_ordering() -> None:
    history_store = InMemoryHistoryStore()
    _ingest_cycle(history_store, captured_at=T0, suffix="baseline", changes=())
    _ingest_cycle(
        history_store,
        captured_at=T2,
        suffix="cycle-2",
        changes=(_change(ChangeType.IMPLEMENTATION_CHANGED, timestamp=T2),),
        risk_previous=_bundle(_evidence("stable", score="10.00"), captured_at=T1),
        risk_current=_bundle(
            _evidence("implementation_changed", source=EvidenceSource.PROXY, severity=EvidenceSeverity.CRITICAL, score="50.00"),
            captured_at=T2,
        ),
    )

    report = TimelineBuilder(history_store=history_store).build(WATCH, generated_at=T3)
    timestamps = [entry.timestamp for entry in report.entries]

    assert timestamps == sorted(timestamps)
    assert report.entries[0].timestamp <= report.entries[-1].timestamp
    assert any(entry.kind.value == "risk_delta" for entry in report.entries)
    assert any(entry.kind.value == "alert" for entry in report.entries)


def test_trend_calculation() -> None:
    history_store = InMemoryHistoryStore()
    _ingest_cycle(history_store, captured_at=T0, suffix="baseline", changes=())
    _ingest_cycle(
        history_store,
        captured_at=T1,
        suffix="cycle-1",
        changes=(_change(ChangeType.GOVERNANCE_CHANGED, timestamp=T1),),
        risk_previous=_bundle(captured_at=T0),
        risk_current=_bundle(_evidence("owner_changed", severity=EvidenceSeverity.HIGH, score="25.00"), captured_at=T1),
    )
    _ingest_cycle(
        history_store,
        captured_at=T2,
        suffix="cycle-2",
        changes=(
            _change(ChangeType.GOVERNANCE_CHANGED, timestamp=T2),
            _change(ChangeType.IMPLEMENTATION_CHANGED, timestamp=T2),
        ),
        risk_previous=_bundle(_evidence("owner_changed", score="25.00"), captured_at=T1),
        risk_current=_bundle(
            _evidence("owner_changed", score="25.00"),
            _evidence("implementation_changed", source=EvidenceSource.PROXY, severity=EvidenceSeverity.CRITICAL, score="50.00"),
            captured_at=T2,
        ),
    )

    records = history_store.list_records(WATCH)
    trends = TrendAnalyzer().analyze(WATCH, records)

    assert trends.risk_trend.direction == RiskTrend.INCREASED
    assert trends.risk_trend.increasing_cycles >= 1
    assert trends.change_recurrence.governance_changes >= 1
    assert trends.change_recurrence.implementation_changes >= 1
    assert trends.alert_frequency.total_alerts >= 1
    assert trends.stability.total_cycles >= 2


def test_retention_policy() -> None:
    baseline_store = InMemoryBaselineStore()
    history_store = InMemoryHistoryStore()
    archiver = SnapshotArchiver(baseline_store=baseline_store, history_store=history_store)
    archiver.archive(_snapshot(captured_at=T0, suffix="baseline"), as_baseline=True)

    for index in range(5):
        captured_at = T0 + timedelta(hours=index + 1)
        _ingest_cycle(history_store, captured_at=captured_at, suffix=f"cycle-{index}", changes=())

    assert len(history_store.list_records(WATCH)) > 3

    manifest = RetentionEngine(
        history_store=history_store,
        baseline_store=baseline_store,
    ).apply(
        WATCH,
        policy=RetentionPolicy(max_records_per_watch=3, max_age_days=0, retain_baseline=True),
        now=T3,
    )

    assert manifest.retained_count <= 3
    assert baseline_store.has_baseline(WATCH)
    baseline_records = [
        item for item in history_store.list_records(WATCH) if item.record_type == HistoryRecordType.SNAPSHOT
    ]
    assert any(item.reference_id == f"{WATCH}:baseline" for item in baseline_records)


def test_deterministic_output() -> None:
    history_store = InMemoryHistoryStore()
    _ingest_cycle(
        history_store,
        captured_at=T1,
        suffix="cycle-1",
        changes=(_change(ChangeType.OWNER_CHANGED, timestamp=T1),),
        risk_previous=_bundle(captured_at=T0),
        risk_current=_bundle(_evidence("owner_changed", severity=EvidenceSeverity.HIGH, score="25.00"), captured_at=T1),
    )

    builder = TimelineBuilder(history_store=history_store)
    first = builder.build(WATCH, generated_at=T3)
    second = builder.build(WATCH, generated_at=T3)

    assert [entry.entry_id for entry in first.entries] == [entry.entry_id for entry in second.entries]
    assert first.trends == second.trends


def test_acknowledgement_timeline_entry() -> None:
    history_store = InMemoryHistoryStore()
    ingestor = HistoryIngestor()
    previous = _bundle(captured_at=T0)
    current = _bundle(_evidence("owner_changed", severity=EvidenceSeverity.HIGH, score="25.00"), captured_at=T1)
    report = _risk_report(previous=previous, current=current)
    batch = AlertEngine().generate(report, generated_at=T1)
    alert = batch.generated_alerts[0]
    acknowledged = AlertEngine().acknowledge(alert)
    history_store.append(ingestor.ingest_acknowledgement(acknowledged))

    timeline = TimelineBuilder(history_store=history_store).build(WATCH, generated_at=T2)

    assert any(entry.kind.value == "acknowledgement" for entry in timeline.entries)
    assert timeline.trends.alert_frequency.acknowledged_alerts == 1
