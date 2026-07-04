"""M4 honeypot intelligence unit tests."""

from app.blockchain.honeypot import (
    BLACKLIST_PROBE_SELECTORS,
    SELL_RESTRICTION_SELECTORS,
    TRADING_ENABLED_SELECTORS,
    TRANSFER_TAX_SELECTORS,
)
from app.blockchain.honeypot_catalog import HONEYPOT_CATALOG, HONEYPOT_FINDING_KEYS
from app.blockchain.honeypot_intelligence import (
    aggregate_detection_method,
    build_honeypot_findings,
    build_honeypot_intelligence_from_legacy,
    build_honeypot_summary,
    legacy_flags_from_findings,
)
from app.blockchain.honeypot_simulation_state import build_not_run_simulation_state
from app.models.enums import (
    HoneypotConfidence,
    HoneypotDetectionMethod,
    HoneypotFindingType,
    HoneypotSeverity,
    HoneypotSimulationStatus,
)


def test_catalog_covers_all_required_findings() -> None:
    required = {
        "trading_gate",
        "whitelist_restriction",
        "blacklist_probe",
        "sell_restriction",
        "transfer_tax_control",
        "modifiable_tax",
        "anti_bot_pattern",
        "high_buy_tax",
        "high_sell_tax",
        "buy_path_blocked",
        "sell_path_blocked",
        "transfer_path_blocked",
        "honeypot_confirmed",
    }
    assert required == HONEYPOT_FINDING_KEYS
    assert len(HONEYPOT_CATALOG) == len(required)


def test_build_findings_detects_bytecode_trading_gate_and_tax() -> None:
    trading_selector = next(iter(TRADING_ENABLED_SELECTORS))
    tax_selector = next(iter(TRANSFER_TAX_SELECTORS))
    bytecode = b"\x60\x80" + trading_selector + tax_selector

    findings = build_honeypot_findings(logic_bytecode=bytecode)
    by_type = {finding.finding_type: finding for finding in findings}

    assert by_type[HoneypotFindingType.TRADING_GATE].enabled is True
    assert by_type[HoneypotFindingType.TRANSFER_TAX_CONTROL].enabled is True
    assert by_type[HoneypotFindingType.TRADING_GATE].detection_method == HoneypotDetectionMethod.BYTECODE
    assert by_type[HoneypotFindingType.SELL_PATH_BLOCKED].enabled is False
    assert by_type[HoneypotFindingType.SELL_PATH_BLOCKED].description.startswith("Not tested")


def test_build_findings_detects_blacklist_sell_composite() -> None:
    blacklist_selector = next(iter(BLACKLIST_PROBE_SELECTORS))
    sell_selector = next(iter(SELL_RESTRICTION_SELECTORS))
    bytecode = b"\x60\x80" + blacklist_selector + sell_selector

    findings = build_honeypot_findings(logic_bytecode=bytecode)
    flags = legacy_flags_from_findings(findings)

    assert flags.blacklist_sell_blocking is True


def test_build_findings_prefers_source_confidence() -> None:
    findings = build_honeypot_findings(
        logic_bytecode=b"\x60\x80",
        abi_function_names={"enabletrading", "iswhitelisted"},
        source_verified=True,
    )
    by_type = {finding.finding_type: finding for finding in findings}

    assert by_type[HoneypotFindingType.TRADING_GATE].enabled is True
    assert by_type[HoneypotFindingType.WHITELIST_RESTRICTION].enabled is True
    assert by_type[HoneypotFindingType.TRADING_GATE].confidence == HoneypotConfidence.MEDIUM
    assert by_type[HoneypotFindingType.TRADING_GATE].detection_method == HoneypotDetectionMethod.SOURCE


def test_build_summary_scores_enabled_findings() -> None:
    trading_selector = next(iter(TRADING_ENABLED_SELECTORS))
    blacklist_selector = next(iter(BLACKLIST_PROBE_SELECTORS))
    sell_selector = next(iter(SELL_RESTRICTION_SELECTORS))
    bytecode = b"\x60\x80" + trading_selector + blacklist_selector + sell_selector

    findings = build_honeypot_findings(logic_bytecode=bytecode)
    simulation = build_not_run_simulation_state()
    summary = build_honeypot_summary(findings, simulation=simulation)

    assert summary.finding_count >= 3
    assert summary.critical_count >= 1
    assert summary.honeypot_score > 0
    assert summary.honeypot_risk in (
        HoneypotSeverity.MEDIUM,
        HoneypotSeverity.HIGH,
        HoneypotSeverity.CRITICAL,
    )
    assert summary.is_suspected is True
    assert summary.is_confirmed is False


def test_simulation_state_defaults_to_not_run() -> None:
    simulation = build_not_run_simulation_state()

    assert simulation.status == HoneypotSimulationStatus.NOT_RUN
    assert simulation.buy.attempted is False
    assert simulation.sell.attempted is False


def test_legacy_compat_adapter_reconstructs_findings() -> None:
    findings, summary, simulation = build_honeypot_intelligence_from_legacy(
        trading_enabled_control=True,
        whitelist_control=False,
        blacklist_sell_blocking=True,
        transfer_tax_control=True,
        trade_simulated=False,
        can_buy=None,
        can_sell=None,
        buy_tax_bps=None,
        sell_tax_bps=None,
    )

    by_type = {finding.finding_type: finding for finding in findings}
    assert by_type[HoneypotFindingType.TRADING_GATE].enabled is True
    assert by_type[HoneypotFindingType.BLACKLIST_PROBE].enabled is True
    assert summary.is_suspected is True
    assert simulation.status == HoneypotSimulationStatus.NOT_RUN


def test_build_findings_enriches_confirmed_honeypot_from_simulation() -> None:
    findings = build_honeypot_findings(
        logic_bytecode=b"\x60\x80",
        trade_simulated=True,
        can_buy=True,
        can_sell=False,
        can_transfer=True,
        buy_tax_bps=300,
        sell_tax_bps=9900,
    )
    by_type = {finding.finding_type: finding for finding in findings}
    simulation = build_not_run_simulation_state()
    simulation.status = HoneypotSimulationStatus.COMPLETED
    simulation.sell.attempted = True
    simulation.sell.success = False

    summary = build_honeypot_summary(findings, simulation=simulation)

    assert by_type[HoneypotFindingType.SELL_PATH_BLOCKED].enabled is True
    assert by_type[HoneypotFindingType.HONEYPOT_CONFIRMED].enabled is True
    assert by_type[HoneypotFindingType.HIGH_SELL_TAX].enabled is True
    assert by_type[HoneypotFindingType.TRANSFER_PATH_BLOCKED].enabled is False
    assert summary.is_confirmed is True
    assert summary.honeypot_score >= 90
    assert summary.honeypot_risk == HoneypotSeverity.CRITICAL


def test_aggregate_detection_method_from_findings() -> None:
    findings = build_honeypot_findings(
        logic_bytecode=b"\x60\x80",
        abi_function_names={"enabletrading"},
        source_verified=True,
    )

    assert aggregate_detection_method(findings) == HoneypotDetectionMethod.SOURCE
