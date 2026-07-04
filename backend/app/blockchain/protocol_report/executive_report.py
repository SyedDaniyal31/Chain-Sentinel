"""Executive protocol report builder (M8.4)."""

from __future__ import annotations

import hashlib
from typing import Any

from app.blockchain.protocol_report.models import ProtocolExecutiveReport
from app.blockchain.protocol_report.protocol_score import (
    ProtocolScoreCalculator,
    overall_protocol_risk,
)
from app.blockchain.protocol_report.recommendation_engine import RecommendationEngine
from app.blockchain.protocol_report.summary_builder import ProtocolSummaryBuilder
from app.blockchain.protocol_scheduler.models import NodeScanStatus, ProtocolScanResult


class ProtocolExecutiveReportBuilder:
    """Builds a deterministic executive protocol security report from scan output."""

    def __init__(
        self,
        summary_builder: ProtocolSummaryBuilder | None = None,
        score_calculator: ProtocolScoreCalculator | None = None,
        recommendation_engine: RecommendationEngine | None = None,
    ) -> None:
        self._summary_builder = summary_builder or ProtocolSummaryBuilder()
        self._score_calculator = score_calculator or ProtocolScoreCalculator()
        self._recommendation_engine = recommendation_engine or RecommendationEngine()

    def build(self, scan_result: ProtocolScanResult) -> ProtocolExecutiveReport:
        intelligence = self._summary_builder.build_intelligence(scan_result)
        statistics = self._summary_builder.build_statistics(scan_result, intelligence)
        posture = self._score_calculator.calculate(scan_result, statistics, intelligence)
        overall_score, overall_level = overall_protocol_risk(statistics, posture)
        summary = self._summary_builder.build_summary(
            scan_result,
            statistics,
            overall_score,
            overall_level,
        )
        recommendations = self._recommendation_engine.generate(
            scan_result,
            statistics,
            intelligence,
        )

        return ProtocolExecutiveReport(
            report_id=_build_report_id(scan_result),
            summary=summary,
            statistics=statistics,
            posture=posture,
            intelligence=intelligence,
            recommendations=recommendations,
            node_risk_table=_build_node_risk_table(scan_result),
            metadata={
                "report_version": "M8.4",
                "execution_order": list(scan_result.execution_order),
                "overall_risk_score": str(overall_score),
                "overall_risk_level": overall_level,
            },
        )


def _build_report_id(scan_result: ProtocolScanResult) -> str:
    root = str(scan_result.aggregated_evidence.get("protocol_root", "unknown"))
    completed = ",".join(sorted(scan_result.completed_nodes))
    digest = hashlib.sha256(f"{root}:{completed}".encode()).hexdigest()
    return digest[:16]


def _build_node_risk_table(scan_result: ProtocolScanResult) -> tuple[dict[str, Any], ...]:
    rows: list[dict[str, Any]] = []
    evidence_nodes = scan_result.aggregated_evidence.get("nodes", {})

    for result in sorted(scan_result.node_results, key=lambda item: item.address):
        node_evidence = evidence_nodes.get(result.address, {})
        row: dict[str, Any] = {
            "address": result.address,
            "status": result.status.value,
            "role": node_evidence.get("role", "unknown"),
            "risk_score": node_evidence.get("risk_score"),
            "risk_level": node_evidence.get("risk_level"),
            "error": result.error,
        }
        if result.status == NodeScanStatus.COMPLETED and result.analysis is not None:
            row["risk_score"] = str(result.analysis.risk_score)
            row["risk_level"] = result.analysis.risk_level.value
            row["is_upgradeable"] = result.analysis.is_upgradeable
        rows.append(row)

    return tuple(rows)
