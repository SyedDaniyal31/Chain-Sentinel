"""Unit tests for risk correlation engine (M7.2)."""

from decimal import Decimal

import pytest

from app.blockchain.risk.correlation.builtin_rules import CallableCorrelationRule, register_builtin_rules
from app.blockchain.risk.correlation.engine import RiskCorrelationEngine
from app.blockchain.risk.correlation.evidence_index import EvidenceIndex
from app.blockchain.risk.correlation.matcher import CorrelationMatcher
from app.blockchain.risk.correlation.models import (
    CorrelatedRiskFinding,
    CorrelationImpact,
    CorrelationLikelihood,
    CorrelationRule,
)
from app.blockchain.risk.correlation.registry import (
    CorrelationRuleRegistry,
    DuplicateCorrelationRuleError,
    get_default_registry,
)
from app.blockchain.risk.evidence import create_evidence
from app.blockchain.risk.evidence_builder import RiskEvidenceBuilder, RiskEvidenceBundle
from app.blockchain.risk.evidence_types import (
    EvidenceCategory,
    EvidenceMetadataKey,
    EvidenceSeverity,
    EvidenceSource,
)
from app.blockchain.risk.models import RiskEvidence
from app.blockchain.risk.scoring_weights import SCORE_UPGRADEABLE
from app.models.enums import AdminType, ConfidenceLevel, RiskLevel
from app.schemas.risk import ContractRiskInput
from app.schemas.scan_result import BridgeIntegrationData, ProtocolIntelligenceData
from app.services.risk_engine import RiskEngine


def _signal_evidence(
    *,
    source: EvidenceSource,
    category: EvidenceCategory,
    signal: str,
    score: Decimal | int = Decimal("0.00"),
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM,
    metadata: dict | None = None,
) -> RiskEvidence:
    payload = {EvidenceMetadataKey.SIGNAL.value: signal, **(metadata or {})}
    return create_evidence(
        source=source,
        category=category,
        signal=signal,
        severity=EvidenceSeverity.MEDIUM,
        score=score,
        confidence=confidence,
        reason=f"signal:{signal}",
        metadata=payload,
    )


def test_default_registry_registers_six_builtin_rules() -> None:
    registry = get_default_registry()
    assert len(registry) == 6
    assert registry.get("critical_governance_centralization") is not None
    assert registry.get("exit_liquidity_risk") is not None


def test_registry_rejects_duplicate_rule_ids() -> None:
    registry = CorrelationRuleRegistry()
    rule = CorrelationRule(
        id="duplicate_rule",
        title="Duplicate",
        description="Duplicate registration test",
        severity=EvidenceSeverity.LOW,
        impact=CorrelationImpact.LOW,
        likelihood=CorrelationLikelihood.LOW,
        score_delta=Decimal("0.00"),
    )

    def _never_match(_index: EvidenceIndex, _rule: CorrelationRule) -> None:
        return None

    handler = CallableCorrelationRule(rule=rule, _evaluate=_never_match)
    registry.register(handler)
    with pytest.raises(DuplicateCorrelationRuleError):
        registry.register(handler)


def test_critical_governance_centralization_rule_matches() -> None:
    evidence = [
        _signal_evidence(
            source=EvidenceSource.PROXY,
            category=EvidenceCategory.UPGRADEABILITY,
            signal="is_upgradeable",
            score=SCORE_UPGRADEABLE,
        ),
        _signal_evidence(
            source=EvidenceSource.GOVERNANCE,
            category=EvidenceCategory.AUTHORITY,
            signal="admin_address",
            metadata={
                EvidenceMetadataKey.ADMIN_TYPE.value: AdminType.EOA.value,
                EvidenceMetadataKey.IS_TIMELOCK.value: False,
            },
        ),
    ]

    result = RiskCorrelationEngine().correlate(evidence)

    assert len(result.findings) == 1
    finding = result.findings[0]
    assert finding.correlation_rule == "critical_governance_centralization"
    assert finding.title == "Critical Governance Centralization"
    assert finding.severity == EvidenceSeverity.CRITICAL
    assert len(finding.evidence_ids) == 2


def test_exit_liquidity_risk_rule_matches() -> None:
    evidence = [
        _signal_evidence(
            source=EvidenceSource.CAPABILITY,
            category=EvidenceCategory.CAPABILITY,
            signal="mint_capability",
            score=Decimal("20"),
        ),
        _signal_evidence(
            source=EvidenceSource.LIQUIDITY,
            category=EvidenceCategory.LIQUIDITY,
            signal="no_liquidity",
            score=Decimal("30"),
        ),
    ]

    findings = RiskCorrelationEngine().correlate(evidence).findings
    assert any(item.correlation_rule == "exit_liquidity_risk" for item in findings)


def test_multiple_correlations_fire_simultaneously() -> None:
    evidence = [
        _signal_evidence(
            source=EvidenceSource.PROXY,
            category=EvidenceCategory.UPGRADEABILITY,
            signal="is_upgradeable",
        ),
        _signal_evidence(
            source=EvidenceSource.GOVERNANCE,
            category=EvidenceCategory.AUTHORITY,
            signal="admin_address",
            metadata={EvidenceMetadataKey.ADMIN_TYPE.value: AdminType.EOA.value},
        ),
        _signal_evidence(
            source=EvidenceSource.CAPABILITY,
            category=EvidenceCategory.CAPABILITY,
            signal="mint_capability",
        ),
        _signal_evidence(
            source=EvidenceSource.LIQUIDITY,
            category=EvidenceCategory.LIQUIDITY,
            signal="low_liquidity",
        ),
        _signal_evidence(
            source=EvidenceSource.PROTOCOL,
            category=EvidenceCategory.PROTOCOL,
            signal="bridge:0:Wormhole",
            metadata={EvidenceMetadataKey.SIGNAL.value: "protocol_bridge"},
        ),
    ]

    findings = RiskCorrelationEngine().correlate(evidence).findings
    rule_ids = {finding.correlation_rule for finding in findings}
    assert "critical_governance_centralization" in rule_ids
    assert "exit_liquidity_risk" in rule_ids
    assert "bridge_upgrade_risk" in rule_ids


def test_matcher_prevents_duplicate_rule_matches() -> None:
    registry = CorrelationRuleRegistry()
    rule = CorrelationRule(
        id="always_match",
        title="Always Match",
        description="Always emits a finding",
        severity=EvidenceSeverity.LOW,
        impact=CorrelationImpact.LOW,
        likelihood=CorrelationLikelihood.HIGH,
        score_delta=Decimal("0.00"),
    )

    def _always_match(index: EvidenceIndex, current: CorrelationRule) -> CorrelatedRiskFinding:
        item = index.evidence[0]
        return CorrelatedRiskFinding(
            id=f"correlation:{current.id}",
            title=current.title,
            description=current.description,
            severity=current.severity,
            confidence=ConfidenceLevel.MEDIUM,
            score_delta=current.score_delta,
            impact=current.impact,
            likelihood=current.likelihood,
            explanation="always",
            evidence_ids=(item.id,),
            correlation_rule=current.id,
        )

    registry.register(CallableCorrelationRule(rule=rule, _evaluate=_always_match))
    handler = registry.all_handlers()[0]

    evidence = [_signal_evidence(source=EvidenceSource.SYSTEM, category=EvidenceCategory.SYSTEM, signal="x")]
    findings = CorrelationMatcher().match(evidence, [handler, handler])
    assert len(findings) == 1


def test_confidence_propagates_as_minimum_of_matched_evidence() -> None:
    evidence = [
        _signal_evidence(
            source=EvidenceSource.PROXY,
            category=EvidenceCategory.UPGRADEABILITY,
            signal="is_upgradeable",
            confidence=ConfidenceLevel.HIGH,
        ),
        _signal_evidence(
            source=EvidenceSource.GOVERNANCE,
            category=EvidenceCategory.AUTHORITY,
            signal="admin_address",
            confidence=ConfidenceLevel.LOW,
            metadata={EvidenceMetadataKey.ADMIN_TYPE.value: AdminType.EOA.value},
        ),
    ]

    finding = RiskCorrelationEngine().correlate(evidence).findings[0]
    assert finding.confidence == ConfidenceLevel.LOW


def test_risk_engine_applies_correlation_score_delta() -> None:
    registry = CorrelationRuleRegistry()
    rule = CorrelationRule(
        id="test_score_delta",
        title="Test Score Delta",
        description="Adds ten points when any evidence exists",
        severity=EvidenceSeverity.MEDIUM,
        impact=CorrelationImpact.MEDIUM,
        likelihood=CorrelationLikelihood.HIGH,
        score_delta=Decimal("10.00"),
    )

    def _match_any(index: EvidenceIndex, current: CorrelationRule) -> CorrelatedRiskFinding:
        item = index.evidence[0]
        return CorrelatedRiskFinding(
            id=f"correlation:{current.id}",
            title=current.title,
            description=current.description,
            severity=current.severity,
            confidence=ConfidenceLevel.MEDIUM,
            score_delta=current.score_delta,
            impact=current.impact,
            likelihood=current.likelihood,
            explanation="test",
            evidence_ids=(item.id,),
            correlation_rule=current.id,
        )

    registry.register(CallableCorrelationRule(rule=rule, _evaluate=_match_any))
    engine = RiskEngine(correlation_engine=RiskCorrelationEngine(registry=registry))

    findings_input = ContractRiskInput(
        is_contract=True,
        is_upgradeable=False,
        implementation_address=None,
        admin_address=None,
    )
    baseline = RiskEngine().evaluate_contract_risk(findings_input)
    correlated = engine.evaluate_contract_risk(findings_input)

    assert correlated.risk_score == baseline.risk_score + Decimal("10.00")
    assert correlated.risk_level == RiskLevel.LOW


def test_risk_engine_backward_compatible_with_builtin_correlations() -> None:
    findings = ContractRiskInput(
        is_contract=True,
        is_upgradeable=True,
        implementation_address="0xdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef",
        admin_address="0x1234567890123456789012345678901234567890",
        admin_type=AdminType.EOA,
        mint_capability=True,
        liquidity_analyzed=True,
        has_liquidity=False,
        wallet_analyzed=True,
        deployer_is_fresh=True,
        tornado_funded_deployer=True,
    )
    builder = RiskEvidenceBuilder()
    evidence = builder.from_contract_risk_input(findings)

    correlation = RiskCorrelationEngine().correlate(evidence)
    assert len(correlation.findings) >= 2

    engine = RiskEngine()
    direct = engine.evaluate_contract_risk(findings)
    via_evidence = engine.evaluate_from_evidence(evidence)
    assert direct == via_evidence


def test_contract_input_builder_produces_bridge_correlation_inputs() -> None:
    bundle_evidence = RiskEvidenceBuilder().build(
        RiskEvidenceBundle(
            contract_input=ContractRiskInput(
                is_contract=True,
                is_upgradeable=True,
                implementation_address=None,
                admin_address=None,
            ),
            protocol=ProtocolIntelligenceData(
                protocol_family="bridge",
                protocol_name="Bridge App",
                family="bridge",
                name="Bridge App",
                bridges=[BridgeIntegrationData(name="Wormhole", role="ingress", confidence=80)],
            ),
        )
    )

    findings = RiskCorrelationEngine().correlate(bundle_evidence).findings
    assert any(item.correlation_rule == "bridge_upgrade_risk" for item in findings)


def test_register_builtin_rules_is_idempotent_via_fresh_registry() -> None:
    registry = CorrelationRuleRegistry()
    register_builtin_rules(registry)
    assert len(registry) == 6
