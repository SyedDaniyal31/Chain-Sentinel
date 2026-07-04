"""Liquidity risk integration tests (M5.1)."""

from decimal import Decimal

from app.models.enums import RiskLevel, ThreatLevel
from app.schemas.risk import ContractRiskInput
from app.services.risk_engine import (
    REASON_LOW_LIQUIDITY,
    REASON_NO_LIQUIDITY,
    REASON_SINGLE_WALLET_LP,
    REASON_UNLOCKED_LP,
    RiskEngine,
)


def _base_contract(**overrides: object) -> ContractRiskInput:
    payload = {
        "is_contract": True,
        "is_upgradeable": False,
        "implementation_address": None,
        "admin_address": None,
        "liquidity_analyzed": True,
    }
    payload.update(overrides)
    return ContractRiskInput(**payload)


def test_no_liquidity_adds_weighted_score() -> None:
    result = RiskEngine().evaluate_contract_risk(
        _base_contract(has_liquidity=False, liquidity_usd=Decimal("0.00"))
    )

    assert result.risk_score == Decimal("30.00")
    assert REASON_NO_LIQUIDITY in result.risk_reasons
    assert result.threat_level == ThreatLevel.MEDIUM


def test_low_liquidity_and_unlocked_lp_stack() -> None:
    result = RiskEngine().evaluate_contract_risk(
        _base_contract(
            has_liquidity=True,
            liquidity_usd=Decimal("500.00"),
            liquidity_locked=False,
            liquidity_lock_percentage=Decimal("0.00"),
        )
    )

    assert result.risk_score == Decimal("40.00")
    assert any(REASON_LOW_LIQUIDITY.format(usd=500) in reason for reason in result.risk_reasons)
    assert REASON_UNLOCKED_LP in result.risk_reasons


def test_single_wallet_lp_ownership_adds_risk() -> None:
    result = RiskEngine().evaluate_contract_risk(
        _base_contract(
            has_liquidity=True,
            liquidity_usd=Decimal("25000.00"),
            liquidity_locked=False,
            liquidity_lock_percentage=Decimal("10.00"),
            lp_owner="0x742d35cc6634c0532925a3b844bc9e7595f0beb0",
        )
    )

    assert result.risk_score == Decimal("37.00")
    assert REASON_UNLOCKED_LP in result.risk_reasons
    assert REASON_SINGLE_WALLET_LP in result.risk_reasons


def test_locked_liquidity_does_not_add_unlocked_penalty() -> None:
    result = RiskEngine().evaluate_contract_risk(
        _base_contract(
            has_liquidity=True,
            liquidity_usd=Decimal("50000.00"),
            liquidity_locked=True,
            liquidity_lock_percentage=Decimal("95.00"),
            lp_owner="0x000000000000000000000000000000000000dead",
        )
    )

    assert result.risk_score == Decimal("0.00")
    assert result.risk_level == RiskLevel.LOW
    assert REASON_UNLOCKED_LP not in result.risk_reasons


def test_liquidity_scoring_skipped_when_not_analyzed() -> None:
    result = RiskEngine().evaluate_contract_risk(
        ContractRiskInput(
            is_contract=True,
            is_upgradeable=False,
            implementation_address=None,
            admin_address=None,
            liquidity_analyzed=False,
            has_liquidity=False,
        )
    )

    assert result.risk_score == Decimal("0.00")
    assert REASON_NO_LIQUIDITY not in result.risk_reasons
