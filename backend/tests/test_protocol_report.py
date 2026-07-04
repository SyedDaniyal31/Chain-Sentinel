"""Unit tests for protocol intelligence report builder (M8.4)."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from app.blockchain.protocol_report import (
    ProtocolExecutiveReportBuilder,
    RecommendationSeverity,
    export_report_to_dict,
    export_report_to_json,
)
from app.blockchain.protocol_scheduler.models import (
    ExecutionBatch,
    NodeScanResult,
    NodeScanStatus,
    ProtocolScanMetrics,
    ProtocolScanResult,
    ScanTimingInfo,
)
from app.blockchain.protocol_scan.models import ProtocolRole
from app.models.enums import AdminType, GovernanceType, RiskLevel, UpgradeAuthority
from app.schemas.scan_result import (
    AttackPathData,
    ContractAnalysisData,
    ExternalDependencyData,
    GovernanceRoleData,
    PrivilegedEntityData,
    ProtocolIntelligenceData,
    ProtocolRelationshipData,
    ThreatSurfaceData,
    TrustBoundaryData,
)

ROOT = "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
PROXY = "0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
IMPLEMENTATION = "0xcccccccccccccccccccccccccccccccccccccccc"
GOVERNOR = "0xdddddddddddddddddddddddddddddddddddddddd"
TOKEN = "0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee"
ADMIN = "0x1234567890123456789012345678901234567890"


def _analysis(
    address: str,
    *,
    risk_score: str = "10.00",
    risk_level: RiskLevel = RiskLevel.LOW,
    is_upgradeable: bool = False,
    admin_address: str | None = None,
    admin_type: AdminType | None = None,
    is_timelock: bool = False,
    governance_type: GovernanceType | None = None,
    upgrade_authority: UpgradeAuthority | None = None,
    role_count: int = 0,
    ownership_renounced: bool = False,
    protocol_intelligence: ProtocolIntelligenceData | None = None,
    liquidity_has_liquidity: bool | None = None,
    liquidity_locked: bool | None = None,
    wallet_known_scam: bool = False,
    wallet_tornado: bool = False,
    mint_capability: bool = False,
) -> ContractAnalysisData:
    return ContractAnalysisData(
        chain_id=1,
        latest_block=100,
        is_contract=True,
        bytecode_size=128,
        is_upgradeable=is_upgradeable,
        implementation_address=IMPLEMENTATION.lower() if is_upgradeable and address == PROXY.lower() else None,
        admin_address=admin_address,
        admin_type=admin_type,
        owner_address=None,
        owner_type=None,
        is_timelock=is_timelock,
        min_delay=86400 if is_timelock else None,
        mint_capability=mint_capability,
        pause_capability=False,
        blacklist_capability=False,
        ownership_capability=False,
        trading_enabled_control=False,
        whitelist_control=False,
        blacklist_sell_blocking=False,
        transfer_tax_control=False,
        can_buy=None,
        can_sell=None,
        buy_tax_bps=None,
        sell_tax_bps=None,
        trade_simulated=False,
        risk_score=Decimal(risk_score),
        risk_level=risk_level,
        risk_reasons=[f"scan:{address}"],
        governance_type=governance_type,
        upgrade_authority=upgrade_authority,
        role_count=role_count,
        governance_roles=[
            GovernanceRoleData(name="ADMIN", role_id="0x" + "00" * 32, is_default_admin=True)
        ]
        if role_count
        else None,
        governance_ownership_address=GOVERNOR.lower() if governance_type else None,
        governance_ownership_renounced=ownership_renounced,
        liquidity_has_liquidity=liquidity_has_liquidity,
        liquidity_usd=Decimal("100000.00") if liquidity_has_liquidity else None,
        liquidity_locked=liquidity_locked,
        liquidity_lock_percentage=Decimal("100.00") if liquidity_locked else Decimal("0.00"),
        liquidity_primary_dex="Uniswap V2" if liquidity_has_liquidity else None,
        wallet_reputation_known_scam=wallet_known_scam,
        wallet_tornado_funded_deployer=wallet_tornado,
        wallet_risk_score=80 if wallet_known_scam else 0,
        protocol_intelligence=protocol_intelligence,
    )


def _scan_result(
    *,
    root: str,
    node_analyses: dict[str, ContractAnalysisData],
    roles: dict[str, ProtocolRole] | None = None,
    failed: set[str] | None = None,
    skipped: set[str] | None = None,
    batches: list[tuple[str, ...]] | None = None,
) -> ProtocolScanResult:
    roles = roles or {}
    failed = failed or set()
    skipped = skipped or set()
    now = datetime(2026, 6, 13, 12, 0, tzinfo=timezone.utc)

    node_results: list[NodeScanResult] = []
    nodes_evidence: dict[str, dict[str, str | bool | list[str]]] = {}
    completed: list[str] = []
    execution_order: list[str] = []

    for address in sorted(node_analyses):
        analysis = node_analyses[address]
        if address in failed:
            status = NodeScanStatus.FAILED
            result = NodeScanResult(address=address, status=status, error="scan failed")
        elif address in skipped:
            status = NodeScanStatus.SKIPPED
            result = NodeScanResult(address=address, status=status, error="dependency_failed")
        else:
            status = NodeScanStatus.COMPLETED
            result = NodeScanResult(address=address, status=status, analysis=analysis)
            completed.append(address)
            execution_order.append(address)

        node_results.append(result)
        if status == NodeScanStatus.COMPLETED:
            nodes_evidence[address] = {
                "role": roles.get(address, ProtocolRole.UNKNOWN).value,
                "protocol_name": "sample-protocol",
                "risk_score": str(analysis.risk_score),
                "risk_level": analysis.risk_level.value,
                "risk_reasons": list(analysis.risk_reasons),
                "is_contract": analysis.is_contract,
                "is_upgradeable": analysis.is_upgradeable,
            }

    execution_batches = tuple(
        ExecutionBatch(index, batch)
        for index, batch in enumerate(batches or [(root,)])
    )

    return ProtocolScanResult(
        execution_order=tuple(execution_order),
        completed_nodes=tuple(completed),
        failed_nodes=tuple(sorted(failed)),
        aggregated_evidence={
            "protocol_root": root,
            "node_count": len(node_analyses),
            "completed_count": len(completed),
            "failed_count": len(failed),
            "skipped_count": len(skipped),
            "highest_risk_score": max(
                (str(item.risk_score) for item in node_analyses.values()),
                default="0.00",
            ),
            "risk_levels": sorted({item.risk_level.value for item in node_analyses.values()}),
            "nodes": nodes_evidence,
        },
        metrics=ProtocolScanMetrics(
            nodes_scanned=len(completed),
            parallel_batches_executed=len(execution_batches),
            total_duration_ms=125.0,
            average_node_duration_ms=25.0,
            retry_count=0,
        ),
        timing=ScanTimingInfo(started_at=now, completed_at=now, total_duration_ms=125.0),
        node_results=tuple(node_results),
        execution_batches=execution_batches,
    )


def _protocol_intel(
    *,
    name: str = "sample-protocol",
    family: str = "defi",
    relationships: list[ProtocolRelationshipData] | None = None,
    threat_surface: ThreatSurfaceData | None = None,
) -> ProtocolIntelligenceData:
    return ProtocolIntelligenceData(
        protocol_family=family,
        protocol_name=name,
        family=family,
        name=name,
        integrations=["Uniswap V2"],
        relationships=relationships or [],
        threat_surface=threat_surface or ThreatSurfaceData(),
    )


def test_simple_protocol_report() -> None:
    scan_result = _scan_result(
        root=ROOT,
        node_analyses={
            ROOT: _analysis(
                ROOT,
                protocol_intelligence=_protocol_intel(name="solo-protocol"),
            )
        },
        roles={ROOT: ProtocolRole.ROOT},
    )

    report = ProtocolExecutiveReportBuilder().build(scan_result)

    assert report.summary.protocol_name == "solo-protocol"
    assert report.summary.protocol_root == ROOT
    assert report.statistics.total_nodes == 1
    assert report.statistics.completed_nodes == 1
    assert report.posture.dependency_count == 0
    assert len(report.node_risk_table) == 1


def test_multi_contract_protocol_report() -> None:
    relationship = ProtocolRelationshipData(
        source=ROOT,
        target=TOKEN,
        relationship_type="TOKEN_TO_TREASURY",
        confidence=90,
        detection_source="test",
    )
    threat = ThreatSurfaceData(
        external_dependencies=[
            ExternalDependencyData(
                category="dex",
                name="Uniswap V2",
                confidence=85,
                detection_source="test",
            )
        ],
        trust_boundaries=[
            TrustBoundaryData(
                boundary_type="admin",
                label="Proxy Admin",
                confidence=80,
                detection_source="test",
            )
        ],
        attack_paths=[
            AttackPathData(
                name="Admin takeover",
                steps=["Seize admin", "Upgrade implementation"],
                confidence=75,
                detection_source="test",
            )
        ],
    )
    scan_result = _scan_result(
        root=ROOT,
        node_analyses={
            ROOT: _analysis(
                ROOT,
                protocol_intelligence=_protocol_intel(
                    relationships=[relationship],
                    threat_surface=threat,
                ),
            ),
            TOKEN: _analysis(
                TOKEN,
                risk_score="20.00",
                protocol_intelligence=_protocol_intel(name="sample-protocol"),
            ),
        },
        roles={ROOT: ProtocolRole.ROOT, TOKEN: ProtocolRole.TOKEN},
        batches=[(ROOT,), (TOKEN,)],
    )

    report = ProtocolExecutiveReportBuilder().build(scan_result)

    assert report.statistics.total_nodes == 2
    assert report.intelligence.relationship.relationship_count == 1
    assert report.intelligence.threat.attack_path_count == 1
    assert report.intelligence.threat.trust_boundary_count == 1
    assert report.posture.dependency_count >= 1
    assert report.statistics.integration_count >= 1


def test_governance_heavy_protocol_report() -> None:
    scan_result = _scan_result(
        root=GOVERNOR,
        node_analyses={
            GOVERNOR: _analysis(
                GOVERNOR,
                governance_type=GovernanceType.ACCESS_CONTROL,
                upgrade_authority=UpgradeAuthority.TIMELOCK,
                role_count=3,
                is_timelock=True,
                protocol_intelligence=_protocol_intel(name="governance-protocol", family="governance"),
            ),
        },
        roles={GOVERNOR: ProtocolRole.GOVERNOR},
    )

    report = ProtocolExecutiveReportBuilder().build(scan_result)

    assert report.intelligence.governance.timelock_count == 1
    assert report.intelligence.governance.total_role_count == 3
    assert report.posture.governance_maturity.level.value in {"low", "medium", "high", "critical"}
    assert report.statistics.governance_node_count >= 1


def test_upgradeable_protocol_report() -> None:
    scan_result = _scan_result(
        root=PROXY,
        node_analyses={
            PROXY: _analysis(
                PROXY,
                is_upgradeable=True,
                admin_address=ADMIN,
                admin_type=AdminType.EOA,
                upgrade_authority=UpgradeAuthority.EOA,
                risk_score="35.00",
                protocol_intelligence=_protocol_intel(name="upgradeable-protocol"),
            ),
            IMPLEMENTATION: _analysis(
                IMPLEMENTATION,
                risk_score="15.00",
                protocol_intelligence=_protocol_intel(name="upgradeable-protocol"),
            ),
        },
        roles={PROXY: ProtocolRole.PROXY, IMPLEMENTATION: ProtocolRole.IMPLEMENTATION},
        batches=[(PROXY,), (IMPLEMENTATION,)],
    )

    report = ProtocolExecutiveReportBuilder().build(scan_result)

    assert report.statistics.upgradeable_node_count == 1
    assert report.posture.upgradeability.score > Decimal("0.00")
    assert any(item.category == "upgradeability" for item in report.recommendations)


def test_recommendation_generation() -> None:
    scan_result = _scan_result(
        root=PROXY,
        node_analyses={
            PROXY: _analysis(
                PROXY,
                is_upgradeable=True,
                admin_address=ADMIN,
                admin_type=AdminType.EOA,
                liquidity_has_liquidity=True,
                liquidity_locked=False,
                wallet_known_scam=True,
                risk_score="75.00",
                risk_level=RiskLevel.HIGH,
                protocol_intelligence=_protocol_intel(
                    threat_surface=ThreatSurfaceData(
                        attack_paths=[
                            AttackPathData(
                                name="Rug path",
                                steps=["Remove liquidity"],
                                confidence=80,
                                detection_source="test",
                            )
                        ],
                        privileged_entities=[
                            PrivilegedEntityData(
                                entity_type="admin",
                                label="EOA Admin",
                                confidence=90,
                                detection_source="test",
                            )
                        ],
                    )
                ),
            ),
        },
        roles={PROXY: ProtocolRole.PROXY},
    )

    report = ProtocolExecutiveReportBuilder().build(scan_result)
    categories = {item.category for item in report.recommendations}
    severities = {item.severity for item in report.recommendations}

    assert "wallet" in categories
    assert "upgradeability" in categories
    assert "liquidity" in categories
    assert "risk" in categories
    assert "threat" in categories
    assert RecommendationSeverity.CRITICAL in severities
    assert all(item.rationale for item in report.recommendations)


def test_deterministic_report_output() -> None:
    scan_result = _scan_result(
        root=ROOT,
        node_analyses={
            ROOT: _analysis(
                ROOT,
                protocol_intelligence=_protocol_intel(name="deterministic-protocol"),
            ),
            TOKEN: _analysis(
                TOKEN,
                risk_score="12.00",
                protocol_intelligence=_protocol_intel(name="deterministic-protocol"),
            ),
        },
        roles={ROOT: ProtocolRole.ROOT, TOKEN: ProtocolRole.TOKEN},
        batches=[(ROOT, TOKEN)],
    )

    builder = ProtocolExecutiveReportBuilder()
    report_one = builder.build(scan_result)
    report_two = builder.build(scan_result)

    assert report_one.report_id == report_two.report_id
    assert export_report_to_json(report_one) == export_report_to_json(report_two)
    assert export_report_to_dict(report_one) == export_report_to_dict(report_two)
    assert [item.id for item in report_one.recommendations] == [
        item.id for item in report_two.recommendations
    ]


def test_export_document_structure() -> None:
    from app.blockchain.protocol_report.export import export_report_document

    scan_result = _scan_result(
        root=ROOT,
        node_analyses={ROOT: _analysis(ROOT, protocol_intelligence=_protocol_intel())},
    )
    report = ProtocolExecutiveReportBuilder().build(scan_result)
    document = export_report_document(report)

    assert document["title"] == report.summary.headline
    section_ids = [section["id"] for section in document["sections"]]
    assert section_ids == [
        "summary",
        "posture",
        "statistics",
        "recommendations",
        "node_risk_table",
        "intelligence",
    ]


def test_intelligence_aggregate_includes_risk_evidence() -> None:
    scan_result = _scan_result(
        root=PROXY,
        node_analyses={
            PROXY: _analysis(
                PROXY,
                is_upgradeable=True,
                admin_address=ADMIN,
                admin_type=AdminType.EOA,
                mint_capability=True,
                protocol_intelligence=_protocol_intel(),
            ),
        },
    )

    report = ProtocolExecutiveReportBuilder().build(scan_result)

    assert report.intelligence.risk_evidence
    assert report.statistics.evidence_count == len(report.intelligence.risk_evidence)
    assert report.intelligence.correlated_evidence.finding_count >= 0
