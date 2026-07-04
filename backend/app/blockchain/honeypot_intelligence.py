"""M4 honeypot intelligence builder: findings, summary, and legacy mapping."""

from __future__ import annotations

from app.blockchain.honeypot import HoneypotFlags
from app.blockchain.honeypot_catalog import HONEYPOT_CATALOG, HoneypotFindingDefinition
from app.blockchain.source_analysis_engine import SourceAnalysisResult, SourcePatternHit
from app.blockchain.honeypot_simulation_state import (
    HoneypotSimulationState,
    HoneypotTradePathResult,
    build_not_run_simulation_state,
)
from app.models.enums import (
    HoneypotConfidence,
    HoneypotDetectionMethod,
    HoneypotFindingType,
    HoneypotSeverity,
    HoneypotSimulationStatus,
)
from app.schemas.scan_result import HoneypotFindingData, HoneypotSummaryData

HIGH_SELL_TAX_THRESHOLD_BPS = 5000
HIGH_BUY_TAX_THRESHOLD_BPS = 5000

_SEVERITY_SCORE: dict[HoneypotSeverity, int] = {
    HoneypotSeverity.CRITICAL: 30,
    HoneypotSeverity.HIGH: 18,
    HoneypotSeverity.MEDIUM: 10,
    HoneypotSeverity.LOW: 5,
}

_SEVERITY_CAP: dict[HoneypotSeverity, int | None] = {
    HoneypotSeverity.CRITICAL: 60,
    HoneypotSeverity.HIGH: 36,
    HoneypotSeverity.MEDIUM: None,
    HoneypotSeverity.LOW: None,
}


def build_honeypot_findings(
    *,
    logic_bytecode: bytes,
    abi_function_names: set[str] | None = None,
    source_verified: bool = False,
    trade_simulated: bool = False,
    can_buy: bool | None = None,
    can_sell: bool | None = None,
    can_transfer: bool | None = None,
    buy_tax_bps: int | None = None,
    sell_tax_bps: int | None = None,
) -> list[HoneypotFindingData]:
    """Build the full M4 honeypot finding inventory."""
    names = abi_function_names or set()
    findings: list[HoneypotFindingData] = []

    for definition in HONEYPOT_CATALOG:
        if definition.simulation_only:
            findings.append(_build_simulation_finding(definition, trade_simulated=trade_simulated))
            continue

        hit = _detect_heuristic_finding(
            definition,
            logic_bytecode=logic_bytecode,
            abi_function_names=names,
            source_verified=source_verified,
        )
        findings.append(hit)

    findings = _enrich_simulation_findings(
        findings,
        trade_simulated=trade_simulated,
        can_buy=can_buy,
        can_sell=can_sell,
        can_transfer=can_transfer,
        buy_tax_bps=buy_tax_bps,
        sell_tax_bps=sell_tax_bps,
    )
    return findings


def merge_source_into_honeypot_findings(
    findings: list[HoneypotFindingData],
    source_analysis: SourceAnalysisResult | None,
) -> list[HoneypotFindingData]:
    """Upgrade or enable honeypot findings using verified source intelligence."""
    if source_analysis is None:
        return findings

    mapping: dict[HoneypotFindingType, SourcePatternHit] = {
        HoneypotFindingType.TRADING_GATE: source_analysis.trading_gate,
        HoneypotFindingType.TRANSFER_TAX_CONTROL: source_analysis.tax_controller,
        HoneypotFindingType.MODIFIABLE_TAX: source_analysis.tax_controller,
        HoneypotFindingType.BLACKLIST_PROBE: source_analysis.blacklist,
        HoneypotFindingType.SELL_RESTRICTION: source_analysis.blacklist,
    }

    merged: list[HoneypotFindingData] = []
    for finding in findings:
        hit = mapping.get(finding.finding_type)
        if hit is None or not hit.detected:
            merged.append(finding)
            continue

        definition = next(
            defn for defn in HONEYPOT_CATALOG if defn.finding_type == finding.finding_type
        )
        evidence = list(finding.evidence)
        for item in hit.evidence:
            if item not in evidence:
                evidence.append(item)

        merged.append(
            HoneypotFindingData(
                finding_type=finding.finding_type,
                enabled=True,
                severity=definition.default_severity,
                confidence=HoneypotConfidence.HIGH,
                detection_method=HoneypotDetectionMethod.SOURCE,
                title=definition.title,
                description=definition.description,
                evidence=evidence,
            )
        )

    return merged


def build_honeypot_summary(
    findings: list[HoneypotFindingData],
    *,
    simulation: HoneypotSimulationState | None = None,
) -> HoneypotSummaryData:
    """Aggregate enabled findings into summary metadata and sub-score."""
    enabled = [finding for finding in findings if finding.enabled]
    finding_count = len(enabled)
    critical_count = sum(
        1 for finding in enabled if finding.severity == HoneypotSeverity.CRITICAL
    )

    score = _calculate_honeypot_score(enabled, simulation=simulation)
    honeypot_risk = _score_to_risk_band(score)
    is_suspected = any(
        finding.severity in (HoneypotSeverity.HIGH, HoneypotSeverity.CRITICAL)
        and finding.detection_method != HoneypotDetectionMethod.SIMULATION
        for finding in enabled
    )
    is_confirmed = _is_confirmed_honeypot(findings, simulation=simulation)

    return HoneypotSummaryData(
        finding_count=finding_count,
        critical_count=critical_count,
        honeypot_score=score,
        honeypot_risk=honeypot_risk,
        is_suspected=is_suspected or is_confirmed,
        is_confirmed=is_confirmed,
    )


def legacy_flags_from_findings(findings: list[HoneypotFindingData]) -> HoneypotFlags:
    """Map M4 findings to legacy boolean fields for Risk Engine backward compatibility."""
    by_type = {finding.finding_type: finding for finding in findings}

    trading_gate = _is_enabled(by_type, HoneypotFindingType.TRADING_GATE)
    whitelist = _is_enabled(by_type, HoneypotFindingType.WHITELIST_RESTRICTION)
    blacklist_probe = _is_enabled(by_type, HoneypotFindingType.BLACKLIST_PROBE)
    sell_restriction = _is_enabled(by_type, HoneypotFindingType.SELL_RESTRICTION)
    transfer_tax = (
        _is_enabled(by_type, HoneypotFindingType.TRANSFER_TAX_CONTROL)
        or _is_enabled(by_type, HoneypotFindingType.MODIFIABLE_TAX)
        or _is_enabled(by_type, HoneypotFindingType.HIGH_BUY_TAX)
        or _is_enabled(by_type, HoneypotFindingType.HIGH_SELL_TAX)
    )
    blacklist_sell = (
        (blacklist_probe and sell_restriction)
        or _is_enabled(by_type, HoneypotFindingType.SELL_PATH_BLOCKED)
        or _is_enabled(by_type, HoneypotFindingType.TRANSFER_PATH_BLOCKED)
        or _is_enabled(by_type, HoneypotFindingType.HONEYPOT_CONFIRMED)
    )

    return HoneypotFlags(
        trading_enabled_control=trading_gate,
        whitelist_control=whitelist,
        blacklist_sell_blocking=blacklist_sell,
        transfer_tax_control=transfer_tax,
    )


def aggregate_detection_method(
    findings: list[HoneypotFindingData],
) -> HoneypotDetectionMethod:
    """Derive scan-level honeypot detection method from enabled findings."""
    methods = {
        finding.detection_method
        for finding in findings
        if finding.enabled and finding.detection_method != HoneypotDetectionMethod.NONE
    }
    if HoneypotDetectionMethod.SIMULATION in methods:
        if len(methods) > 1:
            return HoneypotDetectionMethod.BYTECODE
        return HoneypotDetectionMethod.SIMULATION
    if HoneypotDetectionMethod.SOURCE in methods:
        return HoneypotDetectionMethod.SOURCE
    if HoneypotDetectionMethod.BYTECODE in methods:
        return HoneypotDetectionMethod.BYTECODE
    return HoneypotDetectionMethod.NONE


def build_honeypot_intelligence_from_legacy(
    *,
    trading_enabled_control: bool | None,
    whitelist_control: bool | None,
    blacklist_sell_blocking: bool | None,
    transfer_tax_control: bool | None,
    trade_simulated: bool | None,
    can_buy: bool | None,
    can_sell: bool | None,
    buy_tax_bps: int | None,
    sell_tax_bps: int | None,
) -> tuple[list[HoneypotFindingData], HoneypotSummaryData, HoneypotSimulationState]:
    """Reconstruct M4 honeypot intelligence from legacy flat columns (read-path compat)."""
    findings: list[HoneypotFindingData] = []

    for definition in HONEYPOT_CATALOG:
        if definition.simulation_only:
            findings.append(_build_simulation_finding(definition, trade_simulated=bool(trade_simulated)))
            continue

        enabled = _legacy_enables_finding(
            definition.finding_type,
            trading_enabled_control=bool(trading_enabled_control),
            whitelist_control=bool(whitelist_control),
            blacklist_sell_blocking=bool(blacklist_sell_blocking),
            transfer_tax_control=bool(transfer_tax_control),
        )
        findings.append(
            HoneypotFindingData(
                finding_type=definition.finding_type,
                enabled=enabled,
                severity=definition.default_severity,
                confidence=HoneypotConfidence.LOW,
                detection_method=HoneypotDetectionMethod.BYTECODE if enabled else HoneypotDetectionMethod.NONE,
                title=definition.title,
                description=definition.description if enabled else "Not detected in legacy scan record.",
                evidence=[],
            )
        )

    simulation = build_not_run_simulation_state()
    if trade_simulated:
        simulation = build_simulation_state_from_legacy_scalars(
            can_buy=can_buy,
            can_sell=can_sell,
            can_transfer=None,
            buy_tax_bps=buy_tax_bps,
            sell_tax_bps=sell_tax_bps,
        )

    findings = _enrich_simulation_findings(
        findings,
        trade_simulated=bool(trade_simulated),
        can_buy=can_buy,
        can_sell=can_sell,
        can_transfer=None,
        buy_tax_bps=buy_tax_bps,
        sell_tax_bps=sell_tax_bps,
    )
    summary = build_honeypot_summary(findings, simulation=simulation)
    return findings, summary, simulation


def build_simulation_state_from_legacy_scalars(
    *,
    can_buy: bool | None,
    can_sell: bool | None,
    can_transfer: bool | None,
    buy_tax_bps: int | None,
    sell_tax_bps: int | None,
) -> HoneypotSimulationState:
    """Reconstruct a minimal completed simulation snapshot from legacy flat columns."""
    buy = HoneypotTradePathResult(
        attempted=can_buy is not None,
        success=can_buy,
        tax_bps=buy_tax_bps,
    )
    transfer = HoneypotTradePathResult(
        attempted=can_transfer is not None,
        success=can_transfer,
    )
    sell = HoneypotTradePathResult(
        attempted=can_sell is not None,
        success=can_sell,
        tax_bps=sell_tax_bps,
        revert_reason="TRANSFER_FROM_FAILED" if can_sell is False else None,
    )
    round_trip_success = (
        can_buy is True
        and (can_transfer is not False)
        and can_sell is True
    )
    return HoneypotSimulationState(
        status=HoneypotSimulationStatus.COMPLETED,
        buy=buy,
        transfer=transfer,
        sell=sell,
        round_trip_success=round_trip_success,
    )


def _detect_heuristic_finding(
    definition: HoneypotFindingDefinition,
    *,
    logic_bytecode: bytes,
    abi_function_names: set[str],
    source_verified: bool,
) -> HoneypotFindingData:
    evidence: list[str] = []
    from_bytecode = False
    from_source = False

    if logic_bytecode and definition.selectors:
        for selector in definition.selectors:
            if selector in logic_bytecode:
                from_bytecode = True
                evidence.append(f"selector 0x{selector.hex()}")

    if abi_function_names and definition.function_names:
        matched = sorted(names for names in abi_function_names if names in definition.function_names)
        if matched:
            from_source = True
            for name in matched:
                evidence.append(f"function {name}()")

    enabled = from_bytecode or from_source
    if enabled and from_source:
        detection_method = HoneypotDetectionMethod.SOURCE
        confidence = HoneypotConfidence.MEDIUM if source_verified else HoneypotConfidence.LOW
    elif enabled and from_bytecode:
        detection_method = HoneypotDetectionMethod.BYTECODE
        confidence = HoneypotConfidence.LOW
    else:
        detection_method = HoneypotDetectionMethod.NONE
        confidence = HoneypotConfidence.LOW

    return HoneypotFindingData(
        finding_type=definition.finding_type,
        enabled=enabled,
        severity=definition.default_severity,
        confidence=confidence,
        detection_method=detection_method,
        title=definition.title,
        description=definition.description if enabled else definition.description,
        evidence=evidence,
    )


def _build_simulation_finding(
    definition: HoneypotFindingDefinition,
    *,
    trade_simulated: bool,
) -> HoneypotFindingData:
    return HoneypotFindingData(
        finding_type=definition.finding_type,
        enabled=False,
        severity=definition.default_severity,
        confidence=HoneypotConfidence.LOW,
        detection_method=HoneypotDetectionMethod.NONE,
        title=definition.title,
        description=definition.disabled_description or "Not tested — simulation not run.",
        evidence=[],
    )


def _enrich_simulation_findings(
    findings: list[HoneypotFindingData],
    *,
    trade_simulated: bool,
    can_buy: bool | None,
    can_sell: bool | None,
    can_transfer: bool | None,
    buy_tax_bps: int | None,
    sell_tax_bps: int | None,
) -> list[HoneypotFindingData]:
    if not trade_simulated:
        return findings

    updated = list(findings)
    updated = _set_simulation_finding(
        updated,
        HoneypotFindingType.BUY_PATH_BLOCKED,
        enabled=can_buy is False,
        evidence=[f"can_buy={can_buy}"] if can_buy is False else [],
    )
    updated = _set_simulation_finding(
        updated,
        HoneypotFindingType.TRANSFER_PATH_BLOCKED,
        enabled=can_transfer is False,
        evidence=[f"can_transfer={can_transfer}"] if can_transfer is False else [],
    )
    updated = _set_simulation_finding(
        updated,
        HoneypotFindingType.SELL_PATH_BLOCKED,
        enabled=can_sell is False,
        evidence=[f"can_sell={can_sell}"] if can_sell is False else [],
    )
    updated = _set_simulation_finding(
        updated,
        HoneypotFindingType.HIGH_BUY_TAX,
        enabled=buy_tax_bps is not None and buy_tax_bps >= HIGH_BUY_TAX_THRESHOLD_BPS,
        evidence=[f"buy_tax_bps={buy_tax_bps}"] if buy_tax_bps is not None else [],
    )
    updated = _set_simulation_finding(
        updated,
        HoneypotFindingType.HIGH_SELL_TAX,
        enabled=sell_tax_bps is not None and sell_tax_bps >= HIGH_SELL_TAX_THRESHOLD_BPS,
        evidence=[f"sell_tax_bps={sell_tax_bps}"] if sell_tax_bps is not None else [],
    )
    updated = _set_simulation_finding(
        updated,
        HoneypotFindingType.HONEYPOT_CONFIRMED,
        enabled=can_sell is False,
        evidence=["sell_path_blocked"] if can_sell is False else [],
    )
    return updated


def _set_simulation_finding(
    findings: list[HoneypotFindingData],
    finding_type: HoneypotFindingType,
    *,
    enabled: bool,
    evidence: list[str],
) -> list[HoneypotFindingData]:
    definition = next(defn for defn in HONEYPOT_CATALOG if defn.finding_type == finding_type)
    result: list[HoneypotFindingData] = []
    for finding in findings:
        if finding.finding_type != finding_type:
            result.append(finding)
            continue
        result.append(
            HoneypotFindingData(
                finding_type=finding_type,
                enabled=enabled,
                severity=definition.default_severity,
                confidence=HoneypotConfidence.HIGH if enabled else HoneypotConfidence.LOW,
                detection_method=HoneypotDetectionMethod.SIMULATION if enabled else HoneypotDetectionMethod.NONE,
                title=definition.title,
                description=definition.description if enabled else (definition.disabled_description or finding.description),
                evidence=evidence,
            )
        )
    return result


def _calculate_honeypot_score(
    enabled: list[HoneypotFindingData],
    *,
    simulation: HoneypotSimulationState | None,
) -> int:
    totals: dict[HoneypotSeverity, int] = {
        HoneypotSeverity.CRITICAL: 0,
        HoneypotSeverity.HIGH: 0,
        HoneypotSeverity.MEDIUM: 0,
        HoneypotSeverity.LOW: 0,
    }
    for finding in enabled:
        totals[finding.severity] += _SEVERITY_SCORE[finding.severity]

    score = 0
    for severity, points in totals.items():
        cap = _SEVERITY_CAP[severity]
        score += min(points, cap) if cap is not None else points

    if _is_confirmed_honeypot(enabled, simulation=simulation):
        score = max(score, 90)

    for finding in enabled:
        if finding.finding_type == HoneypotFindingType.HIGH_SELL_TAX and finding.enabled:
            score += 20

    return min(score, 100)


def _score_to_risk_band(score: int) -> HoneypotSeverity:
    if score >= 76:
        return HoneypotSeverity.CRITICAL
    if score >= 51:
        return HoneypotSeverity.HIGH
    if score >= 26:
        return HoneypotSeverity.MEDIUM
    return HoneypotSeverity.LOW


def _is_confirmed_honeypot(
    findings: list[HoneypotFindingData],
    *,
    simulation: HoneypotSimulationState | None,
) -> bool:
    by_type = {finding.finding_type: finding for finding in findings}
    if _is_enabled(by_type, HoneypotFindingType.HONEYPOT_CONFIRMED):
        return True
    if _is_enabled(by_type, HoneypotFindingType.SELL_PATH_BLOCKED):
        return True
    if simulation and simulation.status == HoneypotSimulationStatus.COMPLETED:
        return simulation.sell.attempted and simulation.sell.success is False
    return False


def _legacy_enables_finding(
    finding_type: HoneypotFindingType,
    *,
    trading_enabled_control: bool,
    whitelist_control: bool,
    blacklist_sell_blocking: bool,
    transfer_tax_control: bool,
) -> bool:
    if finding_type == HoneypotFindingType.TRADING_GATE:
        return trading_enabled_control
    if finding_type == HoneypotFindingType.WHITELIST_RESTRICTION:
        return whitelist_control
    if finding_type == HoneypotFindingType.BLACKLIST_PROBE:
        return blacklist_sell_blocking
    if finding_type == HoneypotFindingType.SELL_RESTRICTION:
        return blacklist_sell_blocking
    if finding_type in (
        HoneypotFindingType.TRANSFER_TAX_CONTROL,
        HoneypotFindingType.MODIFIABLE_TAX,
    ):
        return transfer_tax_control
    return False


def _is_enabled(
    by_type: dict[HoneypotFindingType, HoneypotFindingData],
    finding_type: HoneypotFindingType,
) -> bool:
    finding = by_type.get(finding_type)
    return finding.enabled if finding is not None else False
