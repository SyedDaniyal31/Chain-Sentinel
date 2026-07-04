"""Protocol intelligence aggregation from scan results (M8.4)."""

from __future__ import annotations

from collections.abc import Iterable
from decimal import Decimal
from typing import Any

from app.blockchain.protocol_scheduler.models import NodeScanResult, NodeScanStatus, ProtocolScanResult
from app.blockchain.risk.correlation.engine import RiskCorrelationEngine
from app.blockchain.risk.evidence_builder import RiskEvidenceBuilder, RiskEvidenceBundle
from app.blockchain.risk.models import RiskEvidence
from app.models.enums import AdminType, ConfidenceLevel, GovernanceType, UpgradeAuthority
from app.schemas.risk import ContractRiskInput
from app.schemas.scan_result import (
    ContractAnalysisData,
    GovernanceAnalysisData,
)
from app.blockchain.protocol_report.models import (
    CorrelatedEvidenceSummary,
    GovernanceIntelligenceSummary,
    LiquidityIntelligenceSummary,
    ProtocolIntelligenceAggregate,
    ProtocolIntelligenceSummary,
    ProtocolStatistics,
    ProtocolSummary,
    RelationshipIntelligenceSummary,
    ThreatIntelligenceSummary,
    WalletIntelligenceSummary,
)


class ProtocolSummaryBuilder:
    """Aggregates ProtocolScanResult into intelligence summaries and statistics."""

    def __init__(
        self,
        evidence_builder: RiskEvidenceBuilder | None = None,
        correlation_engine: RiskCorrelationEngine | None = None,
    ) -> None:
        self._evidence_builder = evidence_builder or RiskEvidenceBuilder()
        self._correlation_engine = correlation_engine or RiskCorrelationEngine()

    def build_intelligence(self, scan_result: ProtocolScanResult) -> ProtocolIntelligenceAggregate:
        completed = self._completed_results(scan_result)
        evidence = self._collect_evidence(completed)
        correlation = self._correlation_engine.correlate(evidence)

        return ProtocolIntelligenceAggregate(
            governance=self._aggregate_governance(completed),
            liquidity=self._aggregate_liquidity(completed),
            wallet=self._aggregate_wallet(completed),
            protocol=self._aggregate_protocol(completed),
            relationship=self._aggregate_relationships(completed),
            threat=self._aggregate_threat(completed),
            correlated_evidence=CorrelatedEvidenceSummary(
                finding_count=len(correlation.findings),
                severities=tuple(
                    sorted({finding.severity.value for finding in correlation.findings})
                ),
                findings=correlation.findings,
            ),
            risk_evidence=tuple(sorted(evidence, key=_evidence_sort_key)),
        )

    def build_statistics(
        self,
        scan_result: ProtocolScanResult,
        intelligence: ProtocolIntelligenceAggregate,
    ) -> ProtocolStatistics:
        completed = self._completed_results(scan_result)
        highest_risk = Decimal("0.00")
        upgradeable_count = 0
        governance_count = 0

        for result in completed:
            analysis = result.analysis
            assert analysis is not None
            if analysis.risk_score > highest_risk:
                highest_risk = analysis.risk_score
            if analysis.is_upgradeable:
                upgradeable_count += 1
            if analysis.governance_type and analysis.governance_type != GovernanceType.NONE:
                governance_count += 1
            elif analysis.role_count:
                governance_count += 1

        skipped_count = sum(
            1 for result in scan_result.node_results if result.status == NodeScanStatus.SKIPPED
        )

        return ProtocolStatistics(
            total_nodes=len(scan_result.node_results),
            completed_nodes=len(completed),
            failed_nodes=len(scan_result.failed_nodes),
            skipped_nodes=skipped_count,
            scan_duration_ms=scan_result.metrics.total_duration_ms,
            parallel_batches=scan_result.metrics.parallel_batches_executed,
            evidence_count=len(intelligence.risk_evidence),
            correlated_finding_count=intelligence.correlated_evidence.finding_count,
            highest_node_risk_score=highest_risk,
            upgradeable_node_count=upgradeable_count,
            governance_node_count=governance_count,
            integration_count=len(intelligence.protocol.integrations),
            relationship_count=intelligence.relationship.relationship_count,
            attack_path_count=intelligence.threat.attack_path_count,
        )

    def build_summary(
        self,
        scan_result: ProtocolScanResult,
        statistics: ProtocolStatistics,
        overall_risk_score: Decimal,
        overall_risk_level: str,
    ) -> ProtocolSummary:
        evidence = scan_result.aggregated_evidence
        protocol_root = str(evidence.get("protocol_root", "unknown"))
        protocol_name = _resolve_protocol_name(scan_result)
        coverage_pct = Decimal("0.00")
        if statistics.total_nodes:
            coverage_pct = (
                Decimal(statistics.completed_nodes) / Decimal(statistics.total_nodes) * Decimal("100")
            ).quantize(Decimal("0.01"))

        key_findings = _build_key_findings(scan_result, statistics)

        return ProtocolSummary(
            protocol_root=protocol_root,
            protocol_name=protocol_name,
            headline=_build_headline(protocol_name, overall_risk_level, statistics),
            overview=_build_overview(protocol_name, statistics, overall_risk_level, coverage_pct),
            overall_risk_level=overall_risk_level,
            overall_risk_score=overall_risk_score,
            key_findings=key_findings,
            scan_coverage_pct=coverage_pct,
            generated_at=scan_result.timing.completed_at,
        )

    def _collect_evidence(
        self,
        completed: Iterable[NodeScanResult],
    ) -> list[RiskEvidence]:
        evidence: list[RiskEvidence] = []
        for result in completed:
            analysis = result.analysis
            if analysis is None:
                continue
            bundle = _analysis_to_evidence_bundle(analysis)
            evidence.extend(self._evidence_builder.build(bundle))
        return evidence

    @staticmethod
    def _completed_results(scan_result: ProtocolScanResult) -> tuple[NodeScanResult, ...]:
        return tuple(
            result
            for result in scan_result.node_results
            if result.status == NodeScanStatus.COMPLETED and result.analysis is not None
        )

    @staticmethod
    def _aggregate_governance(completed: Iterable[NodeScanResult]) -> GovernanceIntelligenceSummary:
        governance_types: set[str] = set()
        upgrade_authorities: set[str] = set()
        admin_addresses: set[str] = set()
        nodes: list[dict[str, Any]] = []
        timelock_count = 0
        renounced_count = 0
        total_roles = 0

        for result in completed:
            analysis = result.analysis
            assert analysis is not None
            if analysis.governance_type:
                governance_types.add(analysis.governance_type.value)
            if analysis.upgrade_authority:
                upgrade_authorities.add(analysis.upgrade_authority.value)
            if analysis.is_timelock:
                timelock_count += 1
            if analysis.governance_ownership_renounced:
                renounced_count += 1
            if analysis.admin_address:
                admin_addresses.add(analysis.admin_address.lower())
            if analysis.role_count:
                total_roles += analysis.role_count

            nodes.append(
                {
                    "address": result.address,
                    "governance_type": analysis.governance_type.value
                    if analysis.governance_type
                    else GovernanceType.NONE.value,
                    "upgrade_authority": analysis.upgrade_authority.value
                    if analysis.upgrade_authority
                    else UpgradeAuthority.NONE.value,
                    "role_count": analysis.role_count or 0,
                    "ownership_renounced": bool(analysis.governance_ownership_renounced),
                    "is_timelock": analysis.is_timelock,
                }
            )

        return GovernanceIntelligenceSummary(
            governance_types=tuple(sorted(governance_types)),
            upgrade_authorities=tuple(sorted(upgrade_authorities)),
            timelock_count=timelock_count,
            renounced_ownership_count=renounced_count,
            total_role_count=total_roles,
            admin_addresses=tuple(sorted(admin_addresses)),
            nodes=tuple(sorted(nodes, key=lambda item: item["address"])),
        )

    @staticmethod
    def _aggregate_liquidity(completed: Iterable[NodeScanResult]) -> LiquidityIntelligenceSummary:
        nodes_with_liquidity = 0
        total_liquidity = Decimal("0.00")
        locked_count = 0
        unlocked_count = 0
        dexes: set[str] = set()
        nodes: list[dict[str, Any]] = []

        for result in completed:
            analysis = result.analysis
            assert analysis is not None
            has_liquidity = bool(analysis.liquidity_has_liquidity)
            liquidity_usd = analysis.liquidity_usd or Decimal("0.00")
            if has_liquidity:
                nodes_with_liquidity += 1
                total_liquidity += liquidity_usd
            if analysis.liquidity_locked:
                locked_count += 1
            elif has_liquidity:
                unlocked_count += 1
            if analysis.liquidity_primary_dex:
                dexes.add(analysis.liquidity_primary_dex)

            nodes.append(
                {
                    "address": result.address,
                    "has_liquidity": has_liquidity,
                    "liquidity_usd": str(liquidity_usd),
                    "liquidity_locked": bool(analysis.liquidity_locked),
                    "primary_dex": analysis.liquidity_primary_dex,
                }
            )

        return LiquidityIntelligenceSummary(
            nodes_with_liquidity=nodes_with_liquidity,
            total_liquidity_usd=total_liquidity,
            locked_pool_count=locked_count,
            unlocked_pool_count=unlocked_count,
            primary_dexes=tuple(sorted(dexes)),
            nodes=tuple(sorted(nodes, key=lambda item: item["address"])),
        )

    @staticmethod
    def _aggregate_wallet(completed: Iterable[NodeScanResult]) -> WalletIntelligenceSummary:
        flagged = 0
        fresh = 0
        tornado = 0
        multisig = 0
        highest_wallet_risk = 0
        nodes: list[dict[str, Any]] = []

        for result in completed:
            analysis = result.analysis
            assert analysis is not None
            if analysis.wallet_reputation_known_scam:
                flagged += 1
            if analysis.wallet_is_fresh_deployer:
                fresh += 1
            if analysis.wallet_tornado_funded_deployer:
                tornado += 1
            if analysis.wallet_treasury_is_multisig:
                multisig += 1
            wallet_risk = analysis.wallet_risk_score or 0
            if wallet_risk > highest_wallet_risk:
                highest_wallet_risk = wallet_risk

            nodes.append(
                {
                    "address": result.address,
                    "known_scam": bool(analysis.wallet_reputation_known_scam),
                    "fresh_deployer": bool(analysis.wallet_is_fresh_deployer),
                    "tornado_funded": bool(analysis.wallet_tornado_funded_deployer),
                    "treasury_multisig": bool(analysis.wallet_treasury_is_multisig),
                    "wallet_risk_score": wallet_risk,
                }
            )

        return WalletIntelligenceSummary(
            flagged_wallet_count=flagged,
            fresh_deployer_count=fresh,
            tornado_funded_count=tornado,
            multisig_treasury_count=multisig,
            highest_wallet_risk_score=highest_wallet_risk,
            nodes=tuple(sorted(nodes, key=lambda item: item["address"])),
        )

    @staticmethod
    def _aggregate_protocol(completed: Iterable[NodeScanResult]) -> ProtocolIntelligenceSummary:
        names: set[str] = set()
        families: set[str] = set()
        standards: set[str] = set()
        integrations: set[str] = set()
        dex_count = 0
        oracle_count = 0
        bridge_count = 0
        vault_count = 0
        nodes: list[dict[str, Any]] = []

        for result in completed:
            analysis = result.analysis
            assert analysis is not None
            protocol = analysis.protocol_intelligence
            if protocol is None:
                nodes.append({"address": result.address, "protocol_name": "unknown"})
                continue

            names.add(protocol.name or protocol.protocol_name)
            families.add(protocol.family or protocol.protocol_family)
            standards.update(protocol.standards)
            integrations.update(protocol.integrations)
            dex_count += len(protocol.dexes)
            oracle_count += len(protocol.oracles)
            bridge_count += len(protocol.bridges)
            vault_count += len(protocol.vaults)

            nodes.append(
                {
                    "address": result.address,
                    "protocol_name": protocol.name or protocol.protocol_name,
                    "protocol_family": protocol.family or protocol.protocol_family,
                    "integration_count": len(protocol.integrations),
                }
            )

        return ProtocolIntelligenceSummary(
            protocol_names=tuple(sorted(names)),
            protocol_families=tuple(sorted(families)),
            standards=tuple(sorted(standards)),
            integrations=tuple(sorted(integrations)),
            dex_count=dex_count,
            oracle_count=oracle_count,
            bridge_count=bridge_count,
            vault_count=vault_count,
            nodes=tuple(sorted(nodes, key=lambda item: item["address"])),
        )

    @staticmethod
    def _aggregate_relationships(
        completed: Iterable[NodeScanResult],
    ) -> RelationshipIntelligenceSummary:
        edges: list[dict[str, Any]] = []
        relationship_types: set[str] = set()
        seen: set[tuple[str, str, str]] = set()

        for result in completed:
            analysis = result.analysis
            assert analysis is not None
            protocol = analysis.protocol_intelligence
            if protocol is None:
                continue
            for relationship in protocol.relationships:
                key = (
                    relationship.source.lower(),
                    relationship.target.lower(),
                    relationship.relationship_type,
                )
                if key in seen:
                    continue
                seen.add(key)
                relationship_types.add(relationship.relationship_type)
                edges.append(
                    {
                        "source": relationship.source.lower(),
                        "target": relationship.target.lower(),
                        "relationship_type": relationship.relationship_type,
                        "confidence": relationship.confidence,
                    }
                )

        sorted_edges = tuple(sorted(edges, key=lambda item: (item["source"], item["target"], item["relationship_type"])))
        return RelationshipIntelligenceSummary(
            relationship_count=len(sorted_edges),
            relationship_types=tuple(sorted(relationship_types)),
            edges=sorted_edges,
        )

    @staticmethod
    def _aggregate_threat(completed: Iterable[NodeScanResult]) -> ThreatIntelligenceSummary:
        external_count = 0
        trust_boundary_count = 0
        privileged_count = 0
        attack_path_count = 0
        critical_asset_count = 0
        attack_paths: set[str] = set()
        privileged_entities: set[str] = set()

        for result in completed:
            analysis = result.analysis
            assert analysis is not None
            protocol = analysis.protocol_intelligence
            if protocol is None:
                continue
            threat = protocol.threat_surface
            external_count += len(threat.external_dependencies)
            trust_boundary_count += len(threat.trust_boundaries)
            privileged_count += len(threat.privileged_entities)
            attack_path_count += len(threat.attack_paths)
            critical_asset_count += len(threat.critical_assets)
            for path in threat.attack_paths:
                attack_paths.add(path.name)
            for entity in threat.privileged_entities:
                privileged_entities.add(entity.label)

        return ThreatIntelligenceSummary(
            external_dependency_count=external_count,
            trust_boundary_count=trust_boundary_count,
            privileged_entity_count=privileged_count,
            attack_path_count=attack_path_count,
            critical_asset_count=critical_asset_count,
            attack_paths=tuple(sorted(attack_paths)),
            privileged_entities=tuple(sorted(privileged_entities)),
        )


def _analysis_to_evidence_bundle(analysis: ContractAnalysisData) -> RiskEvidenceBundle:
    contract_input = ContractRiskInput(
        is_contract=analysis.is_contract,
        is_upgradeable=analysis.is_upgradeable,
        implementation_address=analysis.implementation_address,
        admin_address=analysis.admin_address,
        admin_type=analysis.admin_type,
        owner_address=analysis.owner_address,
        owner_type=analysis.owner_type,
        is_timelock=analysis.is_timelock,
        min_delay=analysis.min_delay,
        mint_capability=analysis.mint_capability,
        pause_capability=analysis.pause_capability,
        blacklist_capability=analysis.blacklist_capability,
        ownership_capability=analysis.ownership_capability,
        trading_enabled_control=analysis.trading_enabled_control,
        whitelist_control=analysis.whitelist_control,
        blacklist_sell_blocking=analysis.blacklist_sell_blocking,
        transfer_tax_control=analysis.transfer_tax_control,
        trade_simulated=analysis.trade_simulated,
        can_buy=analysis.can_buy,
        can_sell=analysis.can_sell,
        buy_tax_bps=analysis.buy_tax_bps,
        sell_tax_bps=analysis.sell_tax_bps,
        is_verified=bool(analysis.is_verified),
        contract_type=analysis.contract_type,
        proxy_type=analysis.proxy_type,
        detection_method=analysis.detection_method,
        has_liquidity=bool(analysis.liquidity_has_liquidity),
        liquidity_usd=analysis.liquidity_usd or Decimal("0.00"),
        liquidity_locked=bool(analysis.liquidity_locked),
        liquidity_lock_percentage=analysis.liquidity_lock_percentage or Decimal("0.00"),
        lp_owner=analysis.liquidity_lp_owner,
        primary_dex=analysis.liquidity_primary_dex,
        liquidity_analyzed=analysis.liquidity_has_liquidity is not None,
        deployer_is_fresh=bool(analysis.wallet_is_fresh_deployer),
        creator_owns_majority=bool(analysis.wallet_creator_owns_majority),
        lp_owner_is_creator=bool(analysis.wallet_lp_owner_is_creator),
        exchange_funded_deployer=bool(analysis.wallet_exchange_funded_deployer),
        tornado_funded_deployer=bool(analysis.wallet_tornado_funded_deployer),
        treasury_is_multisig=bool(analysis.wallet_treasury_is_multisig),
        wallet_known_scam=bool(analysis.wallet_reputation_known_scam),
        wallet_analyzed=analysis.wallet_risk_score is not None,
    )

    governance = None
    if analysis.governance_type is not None:
        governance = GovernanceAnalysisData(
            governance_type=analysis.governance_type,
            upgrade_authority=analysis.upgrade_authority or UpgradeAuthority.NONE,
            has_timelock=analysis.is_timelock,
            role_count=analysis.role_count or 0,
            roles=list(analysis.governance_roles or []),
            ownership_address=analysis.governance_ownership_address,
            ownership_renounced=bool(analysis.governance_ownership_renounced),
            source_confidence=analysis.governance_source_confidence or ConfidenceLevel.LOW,
        )

    return RiskEvidenceBundle(
        contract_input=contract_input,
        governance=governance,
        protocol=analysis.protocol_intelligence,
    )


def _resolve_protocol_name(scan_result: ProtocolScanResult) -> str:
    for result in scan_result.node_results:
        if result.analysis and result.analysis.protocol_intelligence:
            protocol = result.analysis.protocol_intelligence
            name = protocol.name or protocol.protocol_name
            if name and name != "unknown":
                return name
    evidence_nodes = scan_result.aggregated_evidence.get("nodes", {})
    for node in evidence_nodes.values():
        protocol_name = node.get("protocol_name")
        if protocol_name and protocol_name != "unknown":
            return str(protocol_name)
    return "unknown"


def _build_headline(protocol_name: str, risk_level: str, statistics: ProtocolStatistics) -> str:
    return (
        f"{protocol_name} protocol assessment: {risk_level.upper()} risk across "
        f"{statistics.completed_nodes}/{statistics.total_nodes} scanned contracts"
    )


def _build_overview(
    protocol_name: str,
    statistics: ProtocolStatistics,
    risk_level: str,
    coverage_pct: Decimal,
) -> str:
    return (
        f"ChainSentinel analyzed {statistics.completed_nodes} of {statistics.total_nodes} "
        f"discovered contracts in the {protocol_name} protocol ({coverage_pct}% coverage). "
        f"The aggregate posture is {risk_level.upper()} with "
        f"{statistics.evidence_count} normalized evidence items and "
        f"{statistics.correlated_finding_count} correlated findings."
    )


def _build_key_findings(
    scan_result: ProtocolScanResult,
    statistics: ProtocolStatistics,
) -> tuple[str, ...]:
    findings: list[str] = []
    if statistics.upgradeable_node_count:
        findings.append(
            f"{statistics.upgradeable_node_count} upgradeable contract(s) detected"
        )
    if statistics.attack_path_count:
        findings.append(f"{statistics.attack_path_count} inferred attack path(s)")
    if statistics.failed_nodes:
        findings.append(f"{statistics.failed_nodes} contract scan(s) failed")
    if statistics.highest_node_risk_score >= Decimal("50.00"):
        findings.append(
            f"Highest node risk score {statistics.highest_node_risk_score}"
        )
    if not findings:
        findings.append("No elevated protocol-wide signals detected")
    return tuple(findings)


def _evidence_sort_key(evidence: RiskEvidence) -> tuple[str, str, str]:
    return (evidence.source.value, evidence.category.value, evidence.id)
