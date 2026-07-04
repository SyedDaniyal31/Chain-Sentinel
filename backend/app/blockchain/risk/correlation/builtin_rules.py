"""Built-in correlation rules (M7.2)."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from collections.abc import Callable, Sequence

from app.blockchain.risk.correlation.evidence_index import EvidenceIndex
from app.blockchain.risk.correlation.models import (
    CorrelatedRiskFinding,
    CorrelationFindingMetadataKey,
    CorrelationImpact,
    CorrelationLikelihood,
    CorrelationRule,
)
from app.blockchain.risk.correlation.registry import CorrelationRuleRegistry
from app.blockchain.risk.evidence_types import EvidenceSeverity
from app.blockchain.risk.models import RiskEvidence
from app.models.enums import ConfidenceLevel


@dataclass(frozen=True, slots=True)
class CallableCorrelationRule:
    """Adapter that binds immutable rule metadata to a deterministic evaluator."""

    rule: CorrelationRule
    _evaluate: Callable[[EvidenceIndex, CorrelationRule], CorrelatedRiskFinding | None]

    @property
    def definition(self) -> CorrelationRule:
        return self.rule

    def evaluate(self, index: EvidenceIndex) -> CorrelatedRiskFinding | None:
        return self._evaluate(index, self.rule)


def _finding(
    rule: CorrelationRule,
    *,
    matched: Sequence[RiskEvidence],
    explanation: str,
    metadata: dict | None = None,
) -> CorrelatedRiskFinding:
    items = tuple(matched)
    evidence_ids = tuple(item.id for item in items)
    return CorrelatedRiskFinding(
        id=f"correlation:{rule.id}",
        title=rule.title,
        description=rule.description,
        severity=rule.severity,
        confidence=EvidenceIndex.aggregate_confidence(items),
        score_delta=rule.score_delta,
        impact=rule.impact,
        likelihood=rule.likelihood,
        explanation=explanation,
        evidence_ids=evidence_ids,
        correlation_rule=rule.id,
        metadata=dict(metadata or {}),
    )


def _match_critical_governance_centralization(
    index: EvidenceIndex,
    rule: CorrelationRule,
) -> CorrelatedRiskFinding | None:
    if not index.has_signal("is_upgradeable"):
        return None
    if not index.has_admin_eoa_without_timelock():
        return None
    matched = (
        index.items_with_signal("is_upgradeable")
        + index.items_with_signal("admin_address")
    )
    return _finding(
        rule,
        matched=matched,
        explanation=(
            "Upgradeable proxy controlled by an EOA without timelock protection "
            "creates critical governance centralization."
        ),
        metadata={
            CorrelationFindingMetadataKey.CENTRALIZATION_WEIGHT.value: 12,
            CorrelationFindingMetadataKey.THREAT_WEIGHT.value: 8,
        },
    )


def _match_exit_liquidity_risk(
    index: EvidenceIndex,
    rule: CorrelationRule,
) -> CorrelatedRiskFinding | None:
    if not index.has_signal("mint_capability"):
        return None
    if not index.has_any_signal("no_liquidity", "low_liquidity"):
        return None
    liquidity_signal = "no_liquidity" if index.has_signal("no_liquidity") else "low_liquidity"
    matched = index.items_with_signal("mint_capability") + index.items_with_signal(liquidity_signal)
    return _finding(
        rule,
        matched=matched,
        explanation=(
            "Unlimited mint capability combined with shallow or missing liquidity "
            "enables exit liquidity extraction."
        ),
        metadata={CorrelationFindingMetadataKey.THREAT_WEIGHT.value: 10},
    )


def _match_bridge_upgrade_risk(
    index: EvidenceIndex,
    rule: CorrelationRule,
) -> CorrelatedRiskFinding | None:
    if not index.has_signal("is_upgradeable"):
        return None
    bridge_items = tuple(
        item
        for item in index.evidence
        if str(item.metadata.get("signal", "")).startswith("protocol_bridge")
    )
    if not bridge_items:
        return None
    matched = index.items_with_signal("is_upgradeable") + bridge_items
    return _finding(
        rule,
        matched=matched,
        explanation=(
            "Bridge integration on an upgradeable proxy increases the blast radius "
            "of malicious upgrades."
        ),
        metadata={CorrelationFindingMetadataKey.THREAT_WEIGHT.value: 12},
    )


def _match_oracle_manipulation_risk(
    index: EvidenceIndex,
    rule: CorrelationRule,
) -> CorrelatedRiskFinding | None:
    oracle_items = tuple(
        item
        for item in index.evidence
        if str(item.metadata.get("signal", "")).startswith("protocol_oracle")
    )
    if not oracle_items:
        return None
    if not index.has_upgrade_authority():
        return None
    authority_items = index.items_with_signal("admin_address") or index.items_with_signal(
        "is_upgradeable"
    )
    matched = oracle_items + authority_items
    return _finding(
        rule,
        matched=matched,
        explanation=(
            "Oracle dependency combined with upgrade authority enables manipulation "
            "of pricing and dependent protocol logic."
        ),
        metadata={CorrelationFindingMetadataKey.THREAT_WEIGHT.value: 14},
    )


def _match_potential_rug_pull_pattern(
    index: EvidenceIndex,
    rule: CorrelationRule,
) -> CorrelatedRiskFinding | None:
    if not index.has_signal("mint_capability"):
        return None
    if not index.has_signal("fresh_deployer"):
        return None
    if not index.has_low_wallet_reputation():
        return None
    matched = (
        index.items_with_signal("mint_capability")
        + index.items_with_signal("fresh_deployer")
        + (
            index.items_with_signal("wallet_known_scam")
            or index.items_with_signal("tornado_funded_deployer")
        )
    )
    return _finding(
        rule,
        matched=matched,
        explanation=(
            "Fresh deployment, weak wallet reputation, and mint capability form a "
            "classic rug-pull pattern."
        ),
        metadata={
            CorrelationFindingMetadataKey.THREAT_WEIGHT.value: 16,
            CorrelationFindingMetadataKey.FORCE_THREAT_CRITICAL.value: False,
        },
    )


def _match_centralized_administrative_control(
    index: EvidenceIndex,
    rule: CorrelationRule,
) -> CorrelatedRiskFinding | None:
    privileged_items = index.items_with_signal("privileged_entity")
    if not privileged_items:
        return None
    if not index.has_admin_capability():
        return None
    capability_items = tuple(
        item
        for signal in (
            "mint_capability",
            "pause_capability",
            "blacklist_capability",
            "ownership_capability",
        )
        for item in index.items_with_signal(signal)
    )
    matched = privileged_items + capability_items
    return _finding(
        rule,
        matched=matched,
        explanation=(
            "Concentrated privileged entities combined with administrative contract "
            "functions indicate centralized operational control."
        ),
        metadata={CorrelationFindingMetadataKey.CENTRALIZATION_WEIGHT.value: 10},
    )


def register_builtin_rules(registry: CorrelationRuleRegistry) -> None:
    """Register the initial correlation rule library."""
    rules = (
        CorrelationRule(
            id="critical_governance_centralization",
            title="Critical Governance Centralization",
            description=(
                "Upgradeable proxy with EOA upgrade authority and no timelock protection."
            ),
            severity=EvidenceSeverity.CRITICAL,
            impact=CorrelationImpact.CRITICAL,
            likelihood=CorrelationLikelihood.HIGH,
            score_delta=Decimal("0.00"),
            priority=10,
        ),
        CorrelationRule(
            id="exit_liquidity_risk",
            title="Exit Liquidity Risk",
            description="Unlimited mint capability paired with low or missing DEX liquidity.",
            severity=EvidenceSeverity.HIGH,
            impact=CorrelationImpact.HIGH,
            likelihood=CorrelationLikelihood.MEDIUM,
            score_delta=Decimal("0.00"),
            priority=20,
        ),
        CorrelationRule(
            id="bridge_upgrade_risk",
            title="Bridge Upgrade Risk",
            description="Bridge integration on an upgradeable proxy surface.",
            severity=EvidenceSeverity.HIGH,
            impact=CorrelationImpact.HIGH,
            likelihood=CorrelationLikelihood.MEDIUM,
            score_delta=Decimal("0.00"),
            priority=30,
        ),
        CorrelationRule(
            id="oracle_manipulation_risk",
            title="Oracle Manipulation Risk",
            description="Oracle dependency combined with upgrade or admin authority.",
            severity=EvidenceSeverity.HIGH,
            impact=CorrelationImpact.HIGH,
            likelihood=CorrelationLikelihood.MEDIUM,
            score_delta=Decimal("0.00"),
            priority=40,
        ),
        CorrelationRule(
            id="potential_rug_pull_pattern",
            title="Potential Rug Pull Pattern",
            description=(
                "Low wallet reputation, fresh deployment, and mint capability observed together."
            ),
            severity=EvidenceSeverity.CRITICAL,
            impact=CorrelationImpact.CRITICAL,
            likelihood=CorrelationLikelihood.HIGH,
            score_delta=Decimal("0.00"),
            priority=50,
        ),
        CorrelationRule(
            id="centralized_administrative_control",
            title="Centralized Administrative Control",
            description="Privileged entity concentration with administrative contract functions.",
            severity=EvidenceSeverity.HIGH,
            impact=CorrelationImpact.HIGH,
            likelihood=CorrelationLikelihood.MEDIUM,
            score_delta=Decimal("0.00"),
            priority=60,
        ),
    )
    evaluators = (
        _match_critical_governance_centralization,
        _match_exit_liquidity_risk,
        _match_bridge_upgrade_risk,
        _match_oracle_manipulation_risk,
        _match_potential_rug_pull_pattern,
        _match_centralized_administrative_control,
    )
    for rule, evaluator in zip(rules, evaluators, strict=True):
        registry.register(CallableCorrelationRule(rule=rule, _evaluate=evaluator))
