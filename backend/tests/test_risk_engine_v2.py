"""Risk Engine V2 dimension tests (threat, centralization, confidence)."""

from decimal import Decimal

import pytest

from app.models.enums import (
    AdminType,
    CentralizationLevel,
    ConfidenceLevel,
    ContractType,
    ProxyType,
    RiskLevel,
    ScanDetectionMethod,
    ThreatLevel,
)
from app.schemas.risk import ContractRiskInput
from app.services.risk_engine import RiskEngine

IMPLEMENTATION = "0xdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef"
ADMIN = "0x1234567890123456789012345678901234567890"
PROXY_ADMIN = "0xabcdefabcdefabcdefabcdefabcdefabcdefabcd"


@pytest.fixture
def engine() -> RiskEngine:
    return RiskEngine()


def test_v2_preserves_v1_risk_score_for_immutable_contract(engine: RiskEngine) -> None:
    result = engine.evaluate_contract_risk(
        ContractRiskInput(
            is_contract=True,
            is_upgradeable=False,
            implementation_address=None,
            admin_address=None,
        )
    )

    assert result.risk_score == Decimal("0.00")
    assert result.risk_level == RiskLevel.LOW
    assert result.threat_level == ThreatLevel.LOW
    assert result.centralization_level == CentralizationLevel.LOW
    assert result.confidence_level == ConfidenceLevel.LOW


def test_v2_eoa_dimensions(engine: RiskEngine) -> None:
    result = engine.evaluate_contract_risk(
        ContractRiskInput(
            is_contract=False,
            is_upgradeable=False,
            implementation_address=None,
            admin_address=None,
        )
    )

    assert result.threat_level == ThreatLevel.LOW
    assert result.centralization_level == CentralizationLevel.LOW
    assert result.confidence_level == ConfidenceLevel.MEDIUM


def test_v2_threat_medium_from_capabilities(engine: RiskEngine) -> None:
    result = engine.evaluate_contract_risk(
        ContractRiskInput(
            is_contract=True,
            is_upgradeable=False,
            implementation_address=None,
            admin_address=None,
            mint_capability=True,
            pause_capability=True,
        )
    )

    assert result.threat_level == ThreatLevel.MEDIUM
    assert result.risk_level == RiskLevel.MEDIUM


def test_v2_threat_high_from_honeypot_indicators(engine: RiskEngine) -> None:
    result = engine.evaluate_contract_risk(
        ContractRiskInput(
            is_contract=True,
            is_upgradeable=False,
            implementation_address=None,
            admin_address=None,
            trading_enabled_control=True,
            whitelist_control=True,
            blacklist_sell_blocking=True,
            transfer_tax_control=True,
        )
    )

    assert result.threat_level == ThreatLevel.CRITICAL


def test_v2_threat_critical_from_confirmed_sell_block(engine: RiskEngine) -> None:
    result = engine.evaluate_contract_risk(
        ContractRiskInput(
            is_contract=True,
            is_upgradeable=False,
            implementation_address=None,
            admin_address=None,
            trade_simulated=True,
            can_buy=True,
            can_sell=False,
        )
    )

    assert result.threat_level == ThreatLevel.CRITICAL
    assert result.risk_level == RiskLevel.MEDIUM


def test_v2_threat_includes_upgrade_surface(engine: RiskEngine) -> None:
    result = engine.evaluate_contract_risk(
        ContractRiskInput(
            is_contract=True,
            is_upgradeable=True,
            implementation_address=IMPLEMENTATION,
            admin_address=None,
        )
    )

    assert result.threat_level == ThreatLevel.MEDIUM


def test_v2_centralization_low_for_immutable_token(engine: RiskEngine) -> None:
    result = engine.evaluate_contract_risk(
        ContractRiskInput(
            is_contract=True,
            is_upgradeable=False,
            implementation_address=None,
            admin_address=None,
            contract_type=ContractType.ERC20,
        )
    )

    assert result.centralization_level == CentralizationLevel.LOW


def test_v2_centralization_high_for_eoa_admin_proxy(engine: RiskEngine) -> None:
    result = engine.evaluate_contract_risk(
        ContractRiskInput(
            is_contract=True,
            is_upgradeable=True,
            implementation_address=IMPLEMENTATION,
            admin_address=ADMIN,
            admin_type=AdminType.EOA,
        )
    )

    assert result.centralization_level == CentralizationLevel.HIGH
    assert result.risk_level == RiskLevel.HIGH


def test_v2_centralization_medium_for_multisig_admin(engine: RiskEngine) -> None:
    result = engine.evaluate_contract_risk(
        ContractRiskInput(
            is_contract=True,
            is_upgradeable=True,
            implementation_address=IMPLEMENTATION,
            admin_address=ADMIN,
            admin_type=AdminType.MULTISIG,
        )
    )

    assert result.centralization_level == CentralizationLevel.MEDIUM


def test_v2_centralization_low_for_timelock_governance(engine: RiskEngine) -> None:
    result = engine.evaluate_contract_risk(
        ContractRiskInput(
            is_contract=True,
            is_upgradeable=True,
            implementation_address=IMPLEMENTATION,
            admin_address=PROXY_ADMIN,
            admin_type=AdminType.CONTRACT,
            is_timelock=True,
            min_delay=86400,
        )
    )

    assert result.centralization_level == CentralizationLevel.LOW


def test_v2_centralization_medium_for_ownership_capability(engine: RiskEngine) -> None:
    result = engine.evaluate_contract_risk(
        ContractRiskInput(
            is_contract=True,
            is_upgradeable=False,
            implementation_address=None,
            admin_address=None,
            ownership_capability=True,
        )
    )

    assert result.centralization_level == CentralizationLevel.MEDIUM


def test_v2_centralization_high_for_uups_unknown_admin(engine: RiskEngine) -> None:
    result = engine.evaluate_contract_risk(
        ContractRiskInput(
            is_contract=True,
            is_upgradeable=True,
            implementation_address=None,
            admin_address=None,
        )
    )

    assert result.centralization_level == CentralizationLevel.MEDIUM


def test_v2_confidence_high_with_verified_source_and_proxy(engine: RiskEngine) -> None:
    result = engine.evaluate_contract_risk(
        ContractRiskInput(
            is_contract=True,
            is_upgradeable=True,
            implementation_address=IMPLEMENTATION,
            admin_address=ADMIN,
            admin_type=AdminType.EOA,
            is_verified=True,
            contract_type=ContractType.ERC20,
            proxy_type=ProxyType.EIP1967_TRANSPARENT,
            detection_method=ScanDetectionMethod.HYBRID,
            trade_simulated=True,
            can_buy=True,
            can_sell=True,
        )
    )

    assert result.confidence_level == ConfidenceLevel.HIGH


def test_v2_confidence_medium_for_bytecode_only_scan(engine: RiskEngine) -> None:
    result = engine.evaluate_contract_risk(
        ContractRiskInput(
            is_contract=True,
            is_upgradeable=False,
            implementation_address=None,
            admin_address=None,
            contract_type=ContractType.ERC20,
            detection_method=ScanDetectionMethod.BYTECODE,
        )
    )

    assert result.confidence_level == ConfidenceLevel.MEDIUM


def test_v2_confidence_low_for_unresolved_proxy(engine: RiskEngine) -> None:
    result = engine.evaluate_contract_risk(
        ContractRiskInput(
            is_contract=True,
            is_upgradeable=True,
            implementation_address=None,
            admin_address=None,
            contract_type=ContractType.UNKNOWN,
            detection_method=ScanDetectionMethod.BYTECODE,
        )
    )

    assert result.confidence_level == ConfidenceLevel.LOW


def test_v2_backward_compatible_risk_score_unchanged(engine: RiskEngine) -> None:
    """V1 composite score must remain stable when V2 inputs are absent."""
    result = engine.evaluate_contract_risk(
        ContractRiskInput(
            is_contract=True,
            is_upgradeable=True,
            implementation_address=IMPLEMENTATION,
            admin_address=ADMIN,
            admin_type=AdminType.EOA,
            mint_capability=True,
        )
    )

    assert result.risk_score == Decimal("100.00")
    assert result.risk_level == RiskLevel.HIGH


@pytest.mark.asyncio
async def test_get_scan_includes_v2_fields(client) -> None:
    create_response = await client.post(
        "/api/v1/scans",
        json={"scan_type": "contract", "target_address": "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2", "chain_id": 11155111},
    )
    scan_id = create_response.json()["id"]
    response = await client.get(f"/api/v1/scans/{scan_id}")

    assert response.status_code == 200
    result = response.json()["result"]
    assert result["threat_level"] == "low"
    assert result["centralization_level"] == "low"
    assert result["confidence_level"] == "medium"
    assert result["risk_score"] is not None
    assert result["risk_level"] is not None
