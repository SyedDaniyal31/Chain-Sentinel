"""Wallet intelligence risk integration tests (M5.2)."""

from decimal import Decimal

from app.models.enums import RiskLevel
from app.schemas.risk import ContractRiskInput
from app.services.risk_engine import (
    REASON_CREATOR_OWNS_MAJORITY,
    REASON_EXCHANGE_FUNDED_DEPLOYER,
    REASON_FRESH_DEPLOYER,
    REASON_LP_OWNER_IS_CREATOR,
    REASON_TORNADO_FUNDED_DEPLOYER,
    REASON_TREASURY_MULTISIG,
    RiskEngine,
)


def _base_contract(**overrides: object) -> ContractRiskInput:
    payload = {
        "is_contract": True,
        "is_upgradeable": False,
        "implementation_address": None,
        "admin_address": None,
        "liquidity_analyzed": False,
        "wallet_analyzed": True,
    }
    payload.update(overrides)
    return ContractRiskInput(**payload)


def test_fresh_deployer_adds_weighted_score() -> None:
    result = RiskEngine().evaluate_contract_risk(_base_contract(deployer_is_fresh=True))
    assert result.risk_score == Decimal("12.00")
    assert REASON_FRESH_DEPLOYER in result.risk_reasons


def test_creator_owns_majority_and_lp_owner_is_creator_stack() -> None:
    result = RiskEngine().evaluate_contract_risk(
        _base_contract(creator_owns_majority=True, lp_owner_is_creator=True)
    )
    assert result.risk_score == Decimal("43.00")
    assert REASON_CREATOR_OWNS_MAJORITY in result.risk_reasons
    assert REASON_LP_OWNER_IS_CREATOR in result.risk_reasons


def test_tornado_funded_deployer_high_weight() -> None:
    result = RiskEngine().evaluate_contract_risk(_base_contract(tornado_funded_deployer=True))
    assert result.risk_score == Decimal("35.00")
    assert REASON_TORNADO_FUNDED_DEPLOYER in result.risk_reasons


def test_exchange_funded_deployer_reduces_score() -> None:
    result = RiskEngine().evaluate_contract_risk(_base_contract(exchange_funded_deployer=True))
    assert result.risk_score == Decimal("0.00")
    assert REASON_EXCHANGE_FUNDED_DEPLOYER in result.risk_reasons
    assert result.risk_level == RiskLevel.LOW


def test_treasury_multisig_reduces_score() -> None:
    result = RiskEngine().evaluate_contract_risk(
        _base_contract(treasury_is_multisig=True, deployer_is_fresh=True)
    )
    assert result.risk_score == Decimal("2.00")
    assert REASON_TREASURY_MULTISIG in result.risk_reasons


def test_wallet_scoring_skipped_when_not_analyzed() -> None:
    result = RiskEngine().evaluate_contract_risk(
        ContractRiskInput(
            is_contract=True,
            is_upgradeable=False,
            implementation_address=None,
            admin_address=None,
            wallet_analyzed=False,
            deployer_is_fresh=True,
            tornado_funded_deployer=True,
        )
    )
    assert result.risk_score == Decimal("0.00")
    assert REASON_TORNADO_FUNDED_DEPLOYER not in result.risk_reasons
