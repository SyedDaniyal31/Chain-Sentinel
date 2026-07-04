"""Map simulation outcomes to M7 RiskEvidence (M9.4)."""

from __future__ import annotations

from decimal import Decimal

from app.blockchain.risk.evidence import create_evidence, merge_evidence
from app.blockchain.risk.evidence_types import (
    EvidenceCategory,
    EvidenceMetadataKey,
    EvidenceSeverity,
    EvidenceSource,
)
from app.blockchain.risk.models import RiskEvidence
from app.blockchain.runtime.calltrace.models import RuntimeExecutionReport
from app.blockchain.runtime.simulation.models import ScenarioType, SimulatedFinding, SimulationScenario
from app.blockchain.runtime.state.models import RuntimeStateReport
from app.models.enums import ConfidenceLevel

SCENARIO_SIGNALS: dict[ScenarioType, tuple[tuple[str, EvidenceSource, EvidenceCategory, EvidenceSeverity, str], ...]] = {
    ScenarioType.PAUSE: (
        (
            "simulated_pause",
            EvidenceSource.GOVERNANCE,
            EvidenceCategory.AUTHORITY,
            EvidenceSeverity.HIGH,
            "Simulated contract pause state transition",
        ),
    ),
    ScenarioType.UNPAUSE: (
        (
            "simulated_unpause",
            EvidenceSource.GOVERNANCE,
            EvidenceCategory.AUTHORITY,
            EvidenceSeverity.MEDIUM,
            "Simulated contract unpause state transition",
        ),
    ),
    ScenarioType.TIMELOCK_REDUCTION: (
        (
            "simulated_timelock_reduction",
            EvidenceSource.GOVERNANCE,
            EvidenceCategory.AUTHORITY,
            EvidenceSeverity.HIGH,
            "Simulated timelock delay reduction",
        ),
    ),
    ScenarioType.GOVERNANCE_PROPOSAL_EXECUTION: (
        (
            "governance_execution",
            EvidenceSource.GOVERNANCE,
            EvidenceCategory.AUTHORITY,
            EvidenceSeverity.HIGH,
            "Simulated governance proposal execution",
        ),
    ),
}


def map_simulation_evidence(
    *,
    scenario: SimulationScenario,
    execution_report: RuntimeExecutionReport,
    state_report: RuntimeStateReport,
) -> tuple[RiskEvidence, ...]:
    """Merge predicted runtime evidence and annotate with simulation metadata."""
    combined = merge_evidence(
        list(execution_report.risk_evidence),
        list(state_report.risk_evidence),
        _scenario_specific_evidence(scenario),
    )
    annotated = [_annotate(item, scenario) for item in combined]
    return tuple(sorted(annotated, key=lambda item: item.id))


def build_simulated_findings(
    *,
    scenario: SimulationScenario,
    evidence: tuple[RiskEvidence, ...],
) -> tuple[SimulatedFinding, ...]:
    """Derive high-level findings from predicted evidence."""
    findings: list[SimulatedFinding] = []
    for index, item in enumerate(evidence):
        signal = str(item.metadata.get(EvidenceMetadataKey.SIGNAL.value, item.id.split(":")[-1]))
        findings.append(
            SimulatedFinding(
                finding_id=f"{scenario.scenario_id}:finding:{index}",
                scenario_type=scenario.scenario_type,
                signal=signal,
                description=item.reason,
                severity=item.severity.value,
            )
        )
    return tuple(findings)


def _scenario_specific_evidence(scenario: SimulationScenario) -> list[RiskEvidence]:
    mappings = SCENARIO_SIGNALS.get(scenario.scenario_type, ())
    evidence: list[RiskEvidence] = []
    for signal, source, category, severity, reason in mappings:
        evidence.append(
            create_evidence(
                source=source,
                category=category,
                signal=signal,
                severity=severity,
                score=Decimal("0.00"),
                confidence=ConfidenceLevel.MEDIUM,
                reason=reason,
                metadata={
                    EvidenceMetadataKey.SIGNAL.value: signal,
                    EvidenceMetadataKey.REASON_ONLY.value: True,
                    "scenario_id": scenario.scenario_id,
                    "scenario_type": scenario.scenario_type.value,
                    "simulated": True,
                },
            )
        )
    return evidence


def _annotate(item: RiskEvidence, scenario: SimulationScenario) -> RiskEvidence:
    metadata = dict(item.metadata)
    metadata.update(
        {
            "simulated": True,
            "scenario_id": scenario.scenario_id,
            "scenario_type": scenario.scenario_type.value,
            EvidenceMetadataKey.REASON_ONLY.value: True,
        }
    )
    return RiskEvidence(
        id=item.id,
        source=item.source,
        category=item.category,
        severity=item.severity,
        score=Decimal("0.00"),
        confidence=item.confidence,
        reason=item.reason,
        metadata=metadata,
        timestamp=item.timestamp,
    )
