"""Unit tests for unified risk evidence (M7.1)."""

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.blockchain.risk.evidence import create_evidence, evidence_id, merge_evidence
from app.blockchain.risk.evidence_builder import RiskEvidenceBuilder, RiskEvidenceBundle
from app.blockchain.risk.evidence_types import (
    EvidenceCategory,
    EvidenceMetadataKey,
    EvidenceSeverity,
    EvidenceSource,
)
from app.blockchain.risk.models import RiskEvidence
from app.blockchain.risk.scoring_weights import (
    REASON_NO_UPGRADE_SIGNALS,
    REASON_NOT_CONTRACT,
    REASON_UPGRADEABLE,
    SCORE_UPGRADEABLE,
)
from app.models.enums import AdminType, ConfidenceLevel, RiskLevel, ThreatLevel
from app.schemas.risk import ContractRiskInput
from app.schemas.scan_result import (
    AttackPathData,
    ExternalDependencyData,
    GovernanceAnalysisData,
    GovernanceRoleData,
    LiquidityAnalysisData,
    ProtocolIntelligenceData,
    ProtocolRelationshipData,
    ThreatSurfaceData,
    WalletIntelligenceData,
    WalletReputationData,
)
from app.services.risk_engine import RiskEngine


def test_create_evidence_sets_core_fields() -> None:
    timestamp = datetime(2026, 1, 1, tzinfo=UTC)
    evidence = create_evidence(
        source=EvidenceSource.PROXY,
        category=EvidenceCategory.UPGRADEABILITY,
        signal="upgradeable",
        severity=EvidenceSeverity.MEDIUM,
        score=SCORE_UPGRADEABLE,
        confidence=ConfidenceLevel.MEDIUM,
        reason=REASON_UPGRADEABLE,
        metadata={EvidenceMetadataKey.SIGNAL.value: "upgradeable"},
        timestamp=timestamp,
    )

    assert evidence.id == evidence_id(
        EvidenceSource.PROXY,
        EvidenceCategory.UPGRADEABILITY,
        "upgradeable",
    )
    assert evidence.source == EvidenceSource.PROXY
    assert evidence.category == EvidenceCategory.UPGRADEABILITY
    assert evidence.severity == EvidenceSeverity.MEDIUM
    assert evidence.score == Decimal("35")
    assert evidence.confidence == ConfidenceLevel.MEDIUM
    assert evidence.reason == REASON_UPGRADEABLE
    assert evidence.timestamp == timestamp


def test_merge_evidence_deduplicates_by_id() -> None:
    first = create_evidence(
        source=EvidenceSource.SYSTEM,
        category=EvidenceCategory.SYSTEM,
        signal="a",
        severity=EvidenceSeverity.INFO,
        reason="first",
    )
    duplicate = create_evidence(
        source=EvidenceSource.SYSTEM,
        category=EvidenceCategory.SYSTEM,
        signal="a",
        severity=EvidenceSeverity.INFO,
        reason="duplicate",
    )
    second = create_evidence(
        source=EvidenceSource.WALLET,
        category=EvidenceCategory.WALLET,
        signal="b",
        severity=EvidenceSeverity.LOW,
        reason="second",
    )

    merged = merge_evidence([first, duplicate], [second])

    assert merged == [first, second]


def test_from_contract_risk_input_upgradeable_only() -> None:
    builder = RiskEvidenceBuilder()
    evidence = builder.from_contract_risk_input(
        ContractRiskInput(
            is_contract=True,
            is_upgradeable=True,
            implementation_address=None,
            admin_address=None,
        )
    )

    upgradeable = next(
        item for item in evidence if item.metadata.get(EvidenceMetadataKey.SIGNAL.value) == "is_upgradeable"
    )
    assert upgradeable.score == Decimal(str(SCORE_UPGRADEABLE))
    assert upgradeable.reason == REASON_UPGRADEABLE
    assert upgradeable.metadata[EvidenceMetadataKey.THREAT_WEIGHT.value] > 0


def test_from_contract_risk_input_eoa() -> None:
    evidence = RiskEvidenceBuilder().from_contract_risk_input(
        ContractRiskInput(
            is_contract=False,
            is_upgradeable=False,
            implementation_address=None,
            admin_address=None,
        )
    )

    assert len(evidence) == 1
    assert evidence[0].reason == REASON_NOT_CONTRACT
    assert evidence[0].metadata[EvidenceMetadataKey.SIGNAL.value] == "not_contract"


def test_from_governance_analysis_adapter() -> None:
    evidence = RiskEvidenceBuilder().from_governance_analysis(
        GovernanceAnalysisData(
            has_timelock=True,
            role_count=1,
            roles=[
                GovernanceRoleData(
                    name="DEFAULT_ADMIN_ROLE",
                    role_id="0x" + "00" * 32,
                )
            ],
        )
    )

    signals = {item.metadata.get(EvidenceMetadataKey.SIGNAL.value) for item in evidence}
    assert "has_timelock" in signals
    assert "governance_role" in signals
    assert all(item.score == Decimal("0.00") for item in evidence)


def test_from_liquidity_analysis_adapter_no_liquidity() -> None:
    evidence = RiskEvidenceBuilder().from_liquidity_analysis(
        LiquidityAnalysisData(has_liquidity=False)
    )

    assert len(evidence) == 1
    assert evidence[0].source == EvidenceSource.LIQUIDITY
    assert evidence[0].score == Decimal("30")


def test_from_wallet_intelligence_adapter() -> None:
    evidence = RiskEvidenceBuilder().from_wallet_intelligence(
        WalletIntelligenceData(
            deployer_is_fresh=True,
            tornado_funded_deployer=True,
            reputation=WalletReputationData(known_scam=True),
        )
    )

    signals = {item.metadata.get(EvidenceMetadataKey.SIGNAL.value) for item in evidence}
    assert {"fresh_deployer", "tornado_funded_deployer", "wallet_known_scam"}.issubset(signals)


def test_from_protocol_and_relationship_adapters() -> None:
    protocol = ProtocolIntelligenceData(
        protocol_family="defi",
        protocol_name="Sample DEX",
        family="defi",
        name="Sample DEX",
        relationships=[
            ProtocolRelationshipData(
                source="Sample DEX",
                target="Uniswap V2",
                relationship_type="TRADES_ON",
                confidence=80,
                detection_source="registry",
            )
        ],
    )
    builder = RiskEvidenceBuilder()

    protocol_evidence = builder.from_protocol_intelligence(protocol)
    relationship_evidence = builder.from_protocol_relationship_analysis(protocol.relationships)

    assert any(item.source == EvidenceSource.PROTOCOL for item in protocol_evidence)
    assert relationship_evidence[0].source == EvidenceSource.RELATIONSHIP
    assert relationship_evidence[0].metadata[EvidenceMetadataKey.RELATIONSHIP_TYPE.value] == "TRADES_ON"
    assert all(item.score == Decimal("0.00") for item in protocol_evidence + relationship_evidence)


def test_from_threat_surface_adapter() -> None:
    evidence = RiskEvidenceBuilder().from_threat_surface_analysis(
        ThreatSurfaceData(
            external_dependencies=[
                ExternalDependencyData(
                    category="oracle",
                    name="Chainlink",
                    confidence=70,
                    detection_source="registry",
                )
            ],
            attack_paths=[
                AttackPathData(
                    name="Oracle manipulation",
                    steps=["Manipulate feed", "Drain vault"],
                    confidence=65,
                    detection_source="heuristic",
                )
            ],
        )
    )

    signals = {item.metadata.get(EvidenceMetadataKey.SIGNAL.value) for item in evidence}
    assert "dependency" in signals
    assert "attack_path" in signals


def test_build_bundle_uses_contract_input_and_supplemental_protocol_evidence() -> None:
    bundle = RiskEvidenceBundle(
        contract_input=ContractRiskInput(
            is_contract=True,
            is_upgradeable=False,
            implementation_address=None,
            admin_address=None,
        ),
        protocol=ProtocolIntelligenceData(
            protocol_family="defi",
            protocol_name="Sample",
            family="defi",
            name="Sample",
        ),
    )

    evidence = RiskEvidenceBuilder().build(bundle)

    assert any(item.reason == REASON_NO_UPGRADE_SIGNALS for item in evidence)
    assert any(item.source == EvidenceSource.PROTOCOL for item in evidence)


def test_risk_engine_evaluate_from_evidence_matches_contract_input_path() -> None:
    findings = ContractRiskInput(
        is_contract=True,
        is_upgradeable=True,
        implementation_address="0xdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef",
        admin_address="0x1234567890123456789012345678901234567890",
        admin_type=AdminType.EOA,
        mint_capability=True,
        trade_simulated=True,
        can_sell=False,
        liquidity_analyzed=True,
        has_liquidity=False,
        wallet_analyzed=True,
        deployer_is_fresh=True,
    )
    engine = RiskEngine()
    builder = RiskEvidenceBuilder()

    direct = engine.evaluate_contract_risk(findings)
    via_evidence = engine.evaluate_from_evidence(builder.from_contract_risk_input(findings))

    assert direct == via_evidence


@pytest.mark.parametrize(
    "findings",
    [
        ContractRiskInput(
            is_contract=True,
            is_upgradeable=False,
            implementation_address=None,
            admin_address=None,
        ),
        ContractRiskInput(
            is_contract=True,
            is_upgradeable=True,
            implementation_address=None,
            admin_address="0x1234567890123456789012345678901234567890",
            admin_type=AdminType.MULTISIG,
            ownership_capability=True,
            trade_simulated=True,
            can_sell=False,
            is_verified=True,
            liquidity_analyzed=True,
            has_liquidity=True,
            liquidity_usd=Decimal("500.00"),
            liquidity_locked=False,
            wallet_analyzed=True,
            tornado_funded_deployer=True,
        ),
    ],
)
def test_risk_engine_public_api_unchanged(findings: ContractRiskInput) -> None:
    engine = RiskEngine()
    evidence = RiskEvidenceBuilder().from_contract_risk_input(findings)

    assert engine.evaluate_contract_risk(findings) == engine.evaluate_from_evidence(evidence)


def test_risk_engine_critical_threat_from_sell_blocked_evidence() -> None:
    evidence = [
        create_evidence(
            source=EvidenceSource.SIMULATION,
            category=EvidenceCategory.HONEYPOT,
            signal="sim_sell_blocked",
            severity=EvidenceSeverity.CRITICAL,
            score=35,
            confidence=ConfidenceLevel.HIGH,
            reason="sell blocked",
            metadata={
                EvidenceMetadataKey.FORCE_THREAT_CRITICAL.value: True,
                EvidenceMetadataKey.THREAT_WEIGHT.value: 40,
            },
        )
    ]

    result = RiskEngine().evaluate_from_evidence(evidence)

    assert result.threat_level == ThreatLevel.CRITICAL


def test_risk_engine_immutable_contract_low_score() -> None:
    findings = ContractRiskInput(
        is_contract=True,
        is_upgradeable=False,
        implementation_address=None,
        admin_address=None,
    )
    result = RiskEngine().evaluate_contract_risk(findings)

    assert result.risk_score == Decimal("0.00")
    assert result.risk_level == RiskLevel.LOW
    assert result.risk_reasons == [REASON_NO_UPGRADE_SIGNALS]
