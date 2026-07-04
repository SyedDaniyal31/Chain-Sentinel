"""Risk correlation engine (M7.2)."""

from __future__ import annotations

from collections.abc import Sequence

from app.blockchain.risk.correlation.matcher import CorrelationMatcher
from app.blockchain.risk.correlation.models import CorrelationResult
from app.blockchain.risk.correlation.registry import CorrelationRuleRegistry, get_default_registry
from app.blockchain.risk.models import RiskEvidence


class RiskCorrelationEngine:
    """Correlates normalized evidence into higher-level security findings."""

    def __init__(
        self,
        registry: CorrelationRuleRegistry | None = None,
        matcher: CorrelationMatcher | None = None,
    ) -> None:
        self._registry = registry or get_default_registry()
        self._matcher = matcher or CorrelationMatcher()

    @property
    def registry(self) -> CorrelationRuleRegistry:
        return self._registry

    def correlate(self, evidence: Sequence[RiskEvidence]) -> CorrelationResult:
        """Evaluate all registered rules against evidence and return correlated findings."""
        handlers = self._registry.all_handlers()
        findings = self._matcher.match(evidence, handlers)
        return CorrelationResult(
            findings=tuple(findings),
            evidence_count=len(evidence),
            rules_evaluated=len(handlers),
        )
