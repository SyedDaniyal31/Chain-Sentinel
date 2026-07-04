"""Evidence indexing and correlation rule matching (M7.2)."""

from __future__ import annotations

from collections.abc import Iterable, Sequence

from app.blockchain.risk.correlation.evidence_index import EvidenceIndex
from app.blockchain.risk.correlation.models import CorrelatedRiskFinding
from app.blockchain.risk.correlation.rule import CorrelationRuleHandler
from app.blockchain.risk.models import RiskEvidence


class CorrelationMatcher:
    """Evaluates registered correlation handlers against indexed evidence."""

    def match(
        self,
        evidence: Sequence[RiskEvidence],
        handlers: Iterable[CorrelationRuleHandler],
    ) -> list[CorrelatedRiskFinding]:
        index = EvidenceIndex(evidence)
        findings: list[CorrelatedRiskFinding] = []
        seen_rule_ids: set[str] = set()
        seen_fingerprints: set[tuple[str, ...]] = set()

        for handler in handlers:
            rule = handler.definition
            if rule.id in seen_rule_ids:
                continue
            finding = handler.evaluate(index)
            if finding is None:
                continue
            fingerprint = finding.evidence_ids
            if fingerprint in seen_fingerprints:
                continue
            findings.append(finding)
            seen_rule_ids.add(rule.id)
            seen_fingerprints.add(fingerprint)

        return findings
