"""RiskEngine unit tests."""

from decimal import Decimal

from app.models.enums import AdminType, RiskLevel
from app.schemas.risk import ContractRiskInput
from app.services.risk_engine import (
    REASON_ADMIN_CONTRACT,
    REASON_ADMIN_EOA,
    REASON_ADMIN_MULTISIG,
    REASON_BLACKLIST_CAPABILITY,
    REASON_BLACKLIST_SELL_BLOCKING,
    REASON_IMPLEMENTATION,
    REASON_MINT_CAPABILITY,
    REASON_NO_UPGRADE_SIGNALS,
    REASON_NOT_CONTRACT,
    REASON_OWNERSHIP_CAPABILITY,
    REASON_PAUSE_CAPABILITY,
    REASON_PROXYADMIN_OWNER,
    REASON_SIM_BUY_BLOCKED,
    REASON_SIM_HIGH_SELL_TAX,
    REASON_SIM_SELL_BLOCKED,
    REASON_TRADING_ENABLED_CONTROL,
    REASON_TRANSFER_TAX_CONTROL,
    REASON_UPGRADEABLE,
    REASON_WHITELIST_CONTROL,
    RiskEngine,
)

IMPLEMENTATION = "0xdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef"
ADMIN = "0x1234567890123456789012345678901234567890"
PROXY_ADMIN = "0xabcdefabcdefabcdefabcdefabcdefabcdefabcd"


def test_risk_engine_low_for_immutable_contract() -> None:
    result = RiskEngine().evaluate_contract_risk(
        ContractRiskInput(
            is_contract=True,
            is_upgradeable=False,
            implementation_address=None,
            admin_address=None,
        )
    )

    assert result.risk_score == Decimal("0.00")
    assert result.risk_level == RiskLevel.LOW
    assert result.risk_reasons == [REASON_NO_UPGRADE_SIGNALS]


def test_risk_engine_low_for_eoa_target() -> None:
    result = RiskEngine().evaluate_contract_risk(
        ContractRiskInput(
            is_contract=False,
            is_upgradeable=False,
            implementation_address=None,
            admin_address=None,
        )
    )

    assert result.risk_score == Decimal("0.00")
    assert result.risk_level == RiskLevel.LOW
    assert result.risk_reasons == [REASON_NOT_CONTRACT]


def test_risk_engine_medium_for_upgradeable_only() -> None:
    result = RiskEngine().evaluate_contract_risk(
        ContractRiskInput(
            is_contract=True,
            is_upgradeable=True,
            implementation_address=None,
            admin_address=None,
        )
    )

    assert result.risk_score == Decimal("35.00")
    assert result.risk_level == RiskLevel.MEDIUM
    assert REASON_UPGRADEABLE in result.risk_reasons


def test_risk_engine_medium_for_uups_style_proxy() -> None:
    result = RiskEngine().evaluate_contract_risk(
        ContractRiskInput(
            is_contract=True,
            is_upgradeable=True,
            implementation_address=IMPLEMENTATION,
            admin_address=None,
        )
    )

    assert result.risk_score == Decimal("65.00")
    assert result.risk_level == RiskLevel.MEDIUM


def test_risk_engine_high_for_eoa_admin_transparent_proxy() -> None:
    result = RiskEngine().evaluate_contract_risk(
        ContractRiskInput(
            is_contract=True,
            is_upgradeable=True,
            implementation_address=IMPLEMENTATION,
            admin_address=ADMIN,
            admin_type=AdminType.EOA,
        )
    )

    assert result.risk_score == Decimal("100.00")
    assert result.risk_level == RiskLevel.HIGH
    assert REASON_ADMIN_EOA in result.risk_reasons


def test_risk_engine_high_for_contract_admin() -> None:
    result = RiskEngine().evaluate_contract_risk(
        ContractRiskInput(
            is_contract=True,
            is_upgradeable=True,
            implementation_address=IMPLEMENTATION,
            admin_address=ADMIN,
            admin_type=AdminType.CONTRACT,
        )
    )

    assert result.risk_score == Decimal("93.00")
    assert result.risk_level == RiskLevel.HIGH
    assert REASON_ADMIN_CONTRACT in result.risk_reasons


def test_risk_engine_high_for_multisig_admin() -> None:
    result = RiskEngine().evaluate_contract_risk(
        ContractRiskInput(
            is_contract=True,
            is_upgradeable=True,
            implementation_address=IMPLEMENTATION,
            admin_address=ADMIN,
            admin_type=AdminType.MULTISIG,
        )
    )

    assert result.risk_score == Decimal("80.00")
    assert result.risk_level == RiskLevel.HIGH
    assert REASON_ADMIN_MULTISIG in result.risk_reasons


def test_risk_engine_high_when_proxyadmin_owner_traced_to_eoa() -> None:
    result = RiskEngine().evaluate_contract_risk(
        ContractRiskInput(
            is_contract=True,
            is_upgradeable=True,
            implementation_address=IMPLEMENTATION,
            admin_address=PROXY_ADMIN,
            admin_type=AdminType.CONTRACT,
            owner_address=ADMIN,
            owner_type=AdminType.EOA,
        )
    )

    assert result.risk_score == Decimal("100.00")
    assert result.risk_level == RiskLevel.HIGH
    assert REASON_ADMIN_EOA in result.risk_reasons
    assert REASON_PROXYADMIN_OWNER in result.risk_reasons


def test_risk_engine_high_when_upgrade_authority_uses_timelock() -> None:
    result = RiskEngine().evaluate_contract_risk(
        ContractRiskInput(
            is_contract=True,
            is_upgradeable=True,
            implementation_address=IMPLEMENTATION,
            admin_address=PROXY_ADMIN,
            admin_type=AdminType.CONTRACT,
            owner_address="0xcccccccccccccccccccccccccccccccccccccccc",
            owner_type=AdminType.CONTRACT,
            is_timelock=True,
            min_delay=86400,
        )
    )

    assert result.risk_score == Decimal("77.00")
    assert result.risk_level == RiskLevel.HIGH
    assert "TimelockController (min delay 86400s)" in result.risk_reasons[2]
    assert REASON_PROXYADMIN_OWNER in result.risk_reasons


def test_risk_engine_timelock_on_admin_slot_directly() -> None:
    result = RiskEngine().evaluate_contract_risk(
        ContractRiskInput(
            is_contract=True,
            is_upgradeable=True,
            implementation_address=IMPLEMENTATION,
            admin_address=PROXY_ADMIN,
            admin_type=AdminType.CONTRACT,
            is_timelock=True,
            min_delay=43200,
        )
    )

    assert result.risk_score == Decimal("77.00")
    assert "min delay 43200s" in result.risk_reasons[-1]


def test_risk_engine_high_when_proxyadmin_owner_traced_to_multisig() -> None:
    result = RiskEngine().evaluate_contract_risk(
        ContractRiskInput(
            is_contract=True,
            is_upgradeable=True,
            implementation_address=IMPLEMENTATION,
            admin_address=PROXY_ADMIN,
            admin_type=AdminType.CONTRACT,
            owner_address=ADMIN,
            owner_type=AdminType.MULTISIG,
        )
    )

    assert result.risk_score == Decimal("80.00")
    assert REASON_ADMIN_MULTISIG in result.risk_reasons
    assert REASON_PROXYADMIN_OWNER in result.risk_reasons


def test_risk_engine_scores_mint_capability() -> None:
    result = RiskEngine().evaluate_contract_risk(
        ContractRiskInput(
            is_contract=True,
            is_upgradeable=False,
            implementation_address=None,
            admin_address=None,
            mint_capability=True,
        )
    )

    assert result.risk_score == Decimal("20.00")
    assert result.risk_level == RiskLevel.LOW
    assert REASON_MINT_CAPABILITY in result.risk_reasons


def test_risk_engine_scores_all_capabilities_capped_at_100() -> None:
    result = RiskEngine().evaluate_contract_risk(
        ContractRiskInput(
            is_contract=True,
            is_upgradeable=True,
            implementation_address=IMPLEMENTATION,
            admin_address=ADMIN,
            admin_type=AdminType.EOA,
            mint_capability=True,
            pause_capability=True,
            blacklist_capability=True,
            ownership_capability=True,
        )
    )

    assert result.risk_score == Decimal("100.00")
    assert result.risk_level == RiskLevel.HIGH
    assert REASON_MINT_CAPABILITY in result.risk_reasons
    assert REASON_PAUSE_CAPABILITY in result.risk_reasons
    assert REASON_BLACKLIST_CAPABILITY in result.risk_reasons
    assert REASON_OWNERSHIP_CAPABILITY in result.risk_reasons


def test_risk_engine_capability_only_token_is_medium() -> None:
    result = RiskEngine().evaluate_contract_risk(
        ContractRiskInput(
            is_contract=True,
            is_upgradeable=False,
            implementation_address=None,
            admin_address=None,
            mint_capability=True,
            pause_capability=True,
            blacklist_capability=True,
            ownership_capability=True,
        )
    )

    assert result.risk_score == Decimal("70.00")
    assert result.risk_level == RiskLevel.HIGH


def test_risk_engine_scores_honeypot_indicators() -> None:
    result = RiskEngine().evaluate_contract_risk(
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

    assert result.risk_score == Decimal("88.00")
    assert result.risk_level == RiskLevel.HIGH
    assert REASON_TRADING_ENABLED_CONTROL in result.risk_reasons
    assert REASON_WHITELIST_CONTROL in result.risk_reasons
    assert REASON_BLACKLIST_SELL_BLOCKING in result.risk_reasons
    assert REASON_TRANSFER_TAX_CONTROL in result.risk_reasons


def test_risk_engine_honeypot_and_governance_capped_at_100() -> None:
    result = RiskEngine().evaluate_contract_risk(
        ContractRiskInput(
            is_contract=True,
            is_upgradeable=True,
            implementation_address=IMPLEMENTATION,
            admin_address=ADMIN,
            admin_type=AdminType.EOA,
            trading_enabled_control=True,
            whitelist_control=True,
            blacklist_sell_blocking=True,
            transfer_tax_control=True,
        )
    )

    assert result.risk_score == Decimal("100.00")
    assert REASON_TRADING_ENABLED_CONTROL in result.risk_reasons
    assert REASON_BLACKLIST_SELL_BLOCKING in result.risk_reasons


def test_risk_engine_scores_confirmed_simulation_honeypot() -> None:
    result = RiskEngine().evaluate_contract_risk(
        ContractRiskInput(
            is_contract=True,
            is_upgradeable=False,
            implementation_address=None,
            admin_address=None,
            trade_simulated=True,
            can_buy=True,
            can_sell=False,
            buy_tax_bps=500,
            sell_tax_bps=9900,
            blacklist_sell_blocking=True,
            transfer_tax_control=True,
        )
    )

    assert result.risk_score == Decimal("60.00")
    assert result.risk_level == RiskLevel.MEDIUM
    assert REASON_SIM_SELL_BLOCKED in result.risk_reasons
    assert REASON_SIM_HIGH_SELL_TAX.format(tax_bps=9900) in result.risk_reasons
    assert REASON_BLACKLIST_SELL_BLOCKING not in result.risk_reasons


def test_risk_engine_simulation_buy_blocked() -> None:
    result = RiskEngine().evaluate_contract_risk(
        ContractRiskInput(
            is_contract=True,
            is_upgradeable=False,
            implementation_address=None,
            admin_address=None,
            trade_simulated=True,
            can_buy=False,
            can_sell=False,
        )
    )

    assert result.risk_score == Decimal("50.00")
    assert REASON_SIM_BUY_BLOCKED in result.risk_reasons
    assert REASON_SIM_SELL_BLOCKED in result.risk_reasons
