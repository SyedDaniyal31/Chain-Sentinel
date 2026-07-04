"""Confidence engine and protocol aggregation tests (M6.1)."""

from app.blockchain.protocol.confidence_engine import compute_confidence
from app.blockchain.protocol.models import (
    DexDetectionResult,
    FrameworkDetection,
    LendingDetectionResult,
    OracleDetectionResult,
    ProtocolDetectionBundle,
    ProtocolFramework,
    ProtocolStandard,
    StandardDetection,
)
from app.blockchain.protocol.protocol_detector import build_detection_reasons, resolve_protocol_identity
from app.models.enums import ConfidenceLevel


def test_compute_confidence_from_multiple_evidence_signals() -> None:
    bundle = ProtocolDetectionBundle(
        standards=[
            StandardDetection(
                standard=ProtocolStandard.ERC20,
                detected=True,
                reason="erc20",
                confidence="high",
            )
        ],
        frameworks=[
            FrameworkDetection(
                framework=ProtocolFramework.OPENZEPPELIN_OWNABLE,
                detected=True,
                reason="ownable",
                confidence="high",
            )
        ],
        detection_reasons=["erc20", "ownable"],
    )
    score = compute_confidence(bundle)
    assert score.score >= 40
    assert score.level in {ConfidenceLevel.MEDIUM.value, ConfidenceLevel.HIGH.value}


def test_compute_confidence_includes_defi_signals() -> None:
    bundle = ProtocolDetectionBundle(
        dexes=[DexDetectionResult(name="Uniswap V3", role="pool", confidence=90)],
        lending=[LendingDetectionResult(name="Aave", role="pool", confidence=85)],
        oracles=[OracleDetectionResult(name="Chainlink", confidence=80)],
        detection_reasons=["dex", "lending", "oracle"],
    )
    score = compute_confidence(bundle)
    assert score.score >= 70
    assert score.level == ConfidenceLevel.HIGH.value


def test_resolve_protocol_identity_prefers_dex_family() -> None:
    bundle = ProtocolDetectionBundle(
        dexes=[DexDetectionResult(name="Uniswap V3", role="pool", confidence=90)],
        standards=[
            StandardDetection(
                standard=ProtocolStandard.ERC20,
                detected=True,
                reason="erc20",
                confidence="high",
            )
        ],
    )
    family, name, _ = resolve_protocol_identity(bundle)
    assert family.value == "dex"
    assert name == "uniswap_v3_pool"


def test_resolve_protocol_identity_stablecoin() -> None:
    bundle = ProtocolDetectionBundle(
        standards=[
            StandardDetection(
                standard=ProtocolStandard.ERC20,
                detected=True,
                reason="erc20",
                confidence="high",
            )
        ],
        verified_source_code="contract USDC is ERC20 {}",
        contract_name="USDC",
    )
    family, name, _ = resolve_protocol_identity(bundle)
    assert family.value == "stablecoin"
    assert name == "usdc_stablecoin"


def test_build_detection_reasons_includes_defi_entries() -> None:
    bundle = ProtocolDetectionBundle(
        dexes=[DexDetectionResult(name="Curve", role="pool", confidence=75)],
        lending=[LendingDetectionResult(name="Aave", role="pool", confidence=80)],
        oracles=[OracleDetectionResult(name="Chainlink", confidence=85)],
    )
    reasons = build_detection_reasons(bundle)
    assert any("DEX detected: Curve" in reason for reason in reasons)
    assert any("Lending detected: Aave" in reason for reason in reasons)
    assert any("Oracle detected: Chainlink" in reason for reason in reasons)


def test_protocol_intelligence_data_accepts_legacy_confidence_string() -> None:
    from app.schemas.scan_result import ProtocolIntelligenceData

    payload = ProtocolIntelligenceData.model_validate(
        {
            "protocol_family": "token",
            "protocol_name": "erc20_token",
            "confidence": "high",
        }
    )
    assert payload.confidence.level.value == "high"
    assert payload.confidence.score == 80
