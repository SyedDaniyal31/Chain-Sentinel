"""Severity and domain mapping for risk posture summaries (M10.4)."""

from __future__ import annotations

from decimal import Decimal

from app.blockchain.continuous.risk_delta.models import RiskEvidenceBundle, RiskSummary
from app.blockchain.risk.evidence_types import EvidenceMetadataKey, EvidenceSeverity, EvidenceSource
from app.blockchain.risk.models import RiskEvidence

SEVERITY_ORDER: tuple[EvidenceSeverity, ...] = (
    EvidenceSeverity.INFO,
    EvidenceSeverity.LOW,
    EvidenceSeverity.MEDIUM,
    EvidenceSeverity.HIGH,
    EvidenceSeverity.CRITICAL,
)

SEVERITY_RANK: dict[EvidenceSeverity, int] = {
    severity: index for index, severity in enumerate(SEVERITY_ORDER)
}

SOURCE_DOMAINS: dict[EvidenceSource, str] = {
    EvidenceSource.GOVERNANCE: "governance",
    EvidenceSource.LIQUIDITY: "liquidity",
    EvidenceSource.WALLET: "wallet",
    EvidenceSource.PROTOCOL: "protocol",
    EvidenceSource.RELATIONSHIP: "relationship",
    EvidenceSource.THREAT_SURFACE: "threat",
    EvidenceSource.PROXY: "protocol",
    EvidenceSource.CAPABILITY: "capability",
    EvidenceSource.HONEYPOT: "honeypot",
    EvidenceSource.SIMULATION: "simulation",
    EvidenceSource.CLASSIFICATION: "classification",
    EvidenceSource.SYSTEM: "system",
}


def intelligence_domain(source: EvidenceSource) -> str:
    """Map evidence source to an intelligence domain label."""
    return SOURCE_DOMAINS.get(source, source.value)


def evidence_signal(evidence: RiskEvidence) -> str:
    """Return a stable signal identifier for an evidence item."""
    signal = evidence.metadata.get(EvidenceMetadataKey.SIGNAL.value)
    if signal:
        return str(signal)
    return evidence.id.split(":")[-1]


def score_contribution(evidence: RiskEvidence) -> Decimal:
    """Return the score contribution for posture aggregation."""
    if evidence.metadata.get(EvidenceMetadataKey.REASON_ONLY.value):
        return Decimal("0.00")
    return Decimal(str(evidence.score))


def summarize_bundle(bundle: RiskEvidenceBundle) -> RiskSummary:
    """Build a risk summary from a posture evidence bundle."""
    return summarize_evidence(bundle.watch_id, bundle.evidence)


def summarize_evidence(watch_id: str, evidence: tuple[RiskEvidence, ...]) -> RiskSummary:
    """Aggregate evidence into a posture summary without invoking RiskEngine."""
    total = Decimal("0.00")
    severity_counts: dict[str, int] = {severity.value: 0 for severity in SEVERITY_ORDER}
    domains: set[str] = set()
    max_severity = EvidenceSeverity.INFO

    for item in evidence:
        total += score_contribution(item)
        severity_counts[item.severity.value] = severity_counts.get(item.severity.value, 0) + 1
        domains.add(intelligence_domain(item.source))
        if SEVERITY_RANK[item.severity] >= SEVERITY_RANK[max_severity]:
            max_severity = item.severity

    return RiskSummary(
        watch_id=watch_id,
        total_score=total,
        evidence_count=len(evidence),
        max_severity=max_severity,
        severity_counts=tuple(sorted(severity_counts.items())),
        intelligence_domains=tuple(sorted(domains)),
    )


def domains_for_evidence(evidence: tuple[RiskEvidence, ...]) -> tuple[str, ...]:
    """Return sorted intelligence domains represented in evidence."""
    return tuple(sorted({intelligence_domain(item.source) for item in evidence}))
