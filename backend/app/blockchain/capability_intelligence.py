"""M3 capability intelligence builder: inventory, controllers, and confidence."""

from __future__ import annotations

from dataclasses import dataclass

from app.blockchain.capability_catalog import CAPABILITY_CATALOG, CapabilityDefinition
from app.blockchain.source_analysis_engine import SourceAnalysisResult
from app.models.enums import (
    CapabilityConfidence,
    CapabilityDetectionMethod,
    CapabilitySeverity,
)
from app.schemas.scan_result import CapabilityDetailData, GovernanceRoleData


@dataclass(frozen=True, slots=True)
class CapabilityDetectionHit:
    """Internal detection result for one capability."""

    enabled: bool
    detection_method: CapabilityDetectionMethod
    confidence: CapabilityConfidence


def build_capability_inventory(
    *,
    logic_bytecode: bytes,
    abi_function_names: set[str] | None = None,
    governance_roles: list[GovernanceRoleData] | None = None,
    ownership_address: str | None = None,
    admin_address: str | None = None,
    owner_address: str | None = None,
    trade_simulated: bool = False,
    buy_tax_bps: int | None = None,
    sell_tax_bps: int | None = None,
    transfer_tax_control: bool = False,
    trading_enabled_control: bool = False,
    whitelist_control: bool = False,
    source_verified: bool = False,
    source_analysis: SourceAnalysisResult | None = None,
) -> dict[str, CapabilityDetailData]:
    """Build the full M3 capability map with controller and severity metadata."""
    role_names = {role.name for role in (governance_roles or [])}
    inventory: dict[str, CapabilityDetailData] = {}

    for definition in CAPABILITY_CATALOG:
        hit = _detect_capability(
            definition,
            logic_bytecode=logic_bytecode,
            abi_function_names=abi_function_names,
            role_names=role_names,
            source_verified=source_verified,
            trade_simulated=trade_simulated,
            buy_tax_bps=buy_tax_bps,
            sell_tax_bps=sell_tax_bps,
            transfer_tax_control=transfer_tax_control,
            trading_enabled_control=trading_enabled_control,
            whitelist_control=whitelist_control,
            source_analysis=source_analysis,
        )
        inventory[definition.key] = CapabilityDetailData(
            enabled=hit.enabled,
            controller=_resolve_controller(
                definition,
                enabled=hit.enabled,
                ownership_address=ownership_address,
                admin_address=admin_address,
                owner_address=owner_address,
                role_names=role_names,
            ),
            severity=definition.default_severity,
            confidence=hit.confidence,
            detection_method=hit.detection_method,
        )

    return inventory


def legacy_flags_from_inventory(
    inventory: dict[str, CapabilityDetailData],
) -> tuple[bool, bool, bool, bool]:
    """Map M3 inventory to legacy boolean fields for backward compatibility."""
    mint = inventory.get("mint", _disabled()).enabled
    pause = inventory.get("pause", _disabled()).enabled
    blacklist = inventory.get("blacklist", _disabled()).enabled
    ownership = (
        inventory.get("transfer_ownership", _disabled()).enabled
        or inventory.get("renounce_ownership", _disabled()).enabled
    )
    return mint, pause, blacklist, ownership


def aggregate_detection_method(
    inventory: dict[str, CapabilityDetailData],
) -> CapabilityDetectionMethod:
    """Derive scan-level capability detection method from enabled capabilities."""
    methods = {
        detail.detection_method
        for detail in inventory.values()
        if detail.enabled and detail.detection_method != CapabilityDetectionMethod.NONE
    }
    if CapabilityDetectionMethod.SOURCE in methods:
        return CapabilityDetectionMethod.SOURCE
    if CapabilityDetectionMethod.SIMULATION in methods:
        if len(methods) > 1:
            return CapabilityDetectionMethod.BYTECODE
        return CapabilityDetectionMethod.SIMULATION
    if CapabilityDetectionMethod.ROLE in methods:
        return CapabilityDetectionMethod.ROLE
    if CapabilityDetectionMethod.BYTECODE in methods:
        return CapabilityDetectionMethod.BYTECODE
    return CapabilityDetectionMethod.NONE


def enabled_capability_count(inventory: dict[str, CapabilityDetailData]) -> int:
    return sum(1 for detail in inventory.values() if detail.enabled)


def _disabled() -> CapabilityDetailData:
    return CapabilityDetailData(
        enabled=False,
        controller=None,
        severity=CapabilitySeverity.LOW,
        confidence=CapabilityConfidence.LOW,
        detection_method=CapabilityDetectionMethod.NONE,
    )


def _detect_capability(
    definition: CapabilityDefinition,
    *,
    logic_bytecode: bytes,
    abi_function_names: set[str] | None,
    role_names: set[str],
    source_verified: bool,
    trade_simulated: bool,
    buy_tax_bps: int | None,
    sell_tax_bps: int | None,
    transfer_tax_control: bool,
    trading_enabled_control: bool,
    whitelist_control: bool,
    source_analysis: SourceAnalysisResult | None,
) -> CapabilityDetectionHit:
    source_hit = _source_pattern_hit(definition.key, source_analysis)
    if source_hit is not None:
        return source_hit

    if definition.key == "buy_tax" and trade_simulated and buy_tax_bps is not None and buy_tax_bps > 0:
        return CapabilityDetectionHit(
            enabled=True,
            detection_method=CapabilityDetectionMethod.SIMULATION,
            confidence=CapabilityConfidence.HIGH,
        )
    if definition.key == "sell_tax" and trade_simulated and sell_tax_bps is not None and sell_tax_bps > 0:
        return CapabilityDetectionHit(
            enabled=True,
            detection_method=CapabilityDetectionMethod.SIMULATION,
            confidence=CapabilityConfidence.HIGH,
        )

    if definition.key == "trading_gate" and trading_enabled_control:
        return _bytecode_hit(source_verified=source_verified)

    if definition.key == "whitelist" and whitelist_control:
        return _bytecode_hit(source_verified=source_verified)

    if definition.key in {"buy_tax", "sell_tax", "dynamic_tax", "treasury_fee", "fee_exemption"}:
        if transfer_tax_control and _bytecode_match(definition, logic_bytecode):
            return _bytecode_hit(source_verified=source_verified)

    normalized_abi = {name.lower() for name in abi_function_names} if abi_function_names else set()
    if normalized_abi and definition.function_names & normalized_abi:
        confidence = CapabilityConfidence.HIGH if source_verified else CapabilityConfidence.MEDIUM
        return CapabilityDetectionHit(
            enabled=True,
            detection_method=CapabilityDetectionMethod.SOURCE,
            confidence=confidence,
        )

    if definition.access_control_role and definition.access_control_role in role_names:
        return CapabilityDetectionHit(
            enabled=True,
            detection_method=CapabilityDetectionMethod.ROLE,
            confidence=CapabilityConfidence.MEDIUM,
        )

    if _bytecode_match(definition, logic_bytecode):
        return _bytecode_hit(source_verified=source_verified)

    return CapabilityDetectionHit(
        enabled=False,
        detection_method=CapabilityDetectionMethod.NONE,
        confidence=CapabilityConfidence.LOW,
    )


def _bytecode_match(definition: CapabilityDefinition, logic_bytecode: bytes) -> bool:
    if not logic_bytecode:
        return False
    return any(selector in logic_bytecode for selector in definition.selectors)


def _bytecode_hit(*, source_verified: bool) -> CapabilityDetectionHit:
    return CapabilityDetectionHit(
        enabled=True,
        detection_method=CapabilityDetectionMethod.BYTECODE,
        confidence=CapabilityConfidence.MEDIUM if source_verified else CapabilityConfidence.LOW,
    )


def _resolve_controller(
    definition: CapabilityDefinition,
    *,
    enabled: bool,
    ownership_address: str | None,
    admin_address: str | None,
    owner_address: str | None,
    role_names: set[str],
) -> str | None:
    if not enabled:
        return None

    if definition.access_control_role and definition.access_control_role in role_names:
        return definition.access_control_role

    if definition.category == "governance_hooks" and "DEFAULT_ADMIN_ROLE" in role_names:
        return "DEFAULT_ADMIN_ROLE"

    if ownership_address:
        return ownership_address

    if owner_address:
        return owner_address

    if admin_address:
        return admin_address

    return "unknown"


def _source_pattern_hit(
    capability_key: str,
    source_analysis: SourceAnalysisResult | None,
) -> CapabilityDetectionHit | None:
    if source_analysis is None:
        return None

    mapping: dict[str, bool] = {
        "mint": False,
        "pause": source_analysis.pausable.detected,
        "blacklist": source_analysis.blacklist.detected,
        "whitelist": False,
        "trading_gate": source_analysis.trading_gate.detected,
        "buy_tax": source_analysis.tax_controller.detected,
        "sell_tax": source_analysis.tax_controller.detected,
        "dynamic_tax": source_analysis.tax_controller.detected,
        "treasury_fee": source_analysis.tax_controller.detected,
        "fee_exemption": source_analysis.tax_controller.detected,
        "transfer_ownership": source_analysis.ownable.detected,
        "renounce_ownership": source_analysis.ownable.detected,
        "grant_role": source_analysis.access_control.detected,
        "revoke_role": source_analysis.access_control.detected,
        "seize": source_analysis.rescue_function.detected,
    }

    if capability_key == "mint":
        mint_names = {"mint", "mintto", "_mint"}
        if source_analysis.abi_function_names & mint_names:
            return CapabilityDetectionHit(
                enabled=True,
                detection_method=CapabilityDetectionMethod.SOURCE,
                confidence=CapabilityConfidence.HIGH,
            )
        return None

    if capability_key not in mapping:
        return None

    if not mapping[capability_key]:
        return None

    return CapabilityDetectionHit(
        enabled=True,
        detection_method=CapabilityDetectionMethod.SOURCE,
        confidence=CapabilityConfidence.HIGH,
    )
