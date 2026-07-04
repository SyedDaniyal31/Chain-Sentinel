"""Protocol executive report export helpers (M8.4)."""

from __future__ import annotations

import json
from decimal import Decimal
from enum import StrEnum
from typing import Any

from app.blockchain.protocol_report.models import (
    ProtocolExecutiveReport,
    ProtocolRecommendation,
    ProtocolSecurityPosture,
    ProtocolSummary,
)


def export_report_to_dict(report: ProtocolExecutiveReport) -> dict[str, Any]:
    """Serialize a protocol executive report into a JSON-compatible dictionary."""
    return {
        "report_id": report.report_id,
        "report_version": report.metadata.get("report_version", "M8.4"),
        "summary": _export_summary(report.summary),
        "statistics": _export_dataclass(report.statistics),
        "posture": _export_posture(report.posture),
        "intelligence": _export_intelligence(report),
        "recommendations": [_export_recommendation(item) for item in report.recommendations],
        "node_risk_table": list(report.node_risk_table),
        "metadata": _normalize(report.metadata),
    }


def export_report_to_json(report: ProtocolExecutiveReport, *, indent: int | None = 2) -> str:
    """Serialize a protocol executive report to deterministic JSON."""
    payload = export_report_to_dict(report)
    return json.dumps(payload, indent=indent, sort_keys=True, default=_json_default)


def export_report_document(report: ProtocolExecutiveReport) -> dict[str, Any]:
    """Produce a structured document payload suitable for future PDF/HTML rendering."""
    exported = export_report_to_dict(report)
    return {
        "title": report.summary.headline,
        "subtitle": f"Protocol root: {report.summary.protocol_root}",
        "generated_at": report.summary.generated_at.isoformat(),
        "sections": [
            {"id": "summary", "title": "Executive Summary", "content": exported["summary"]},
            {"id": "posture", "title": "Security Posture", "content": exported["posture"]},
            {"id": "statistics", "title": "Scan Statistics", "content": exported["statistics"]},
            {
                "id": "recommendations",
                "title": "Recommendations",
                "content": exported["recommendations"],
            },
            {
                "id": "node_risk_table",
                "title": "Contract Risk Table",
                "content": exported["node_risk_table"],
            },
            {
                "id": "intelligence",
                "title": "Protocol Intelligence",
                "content": exported["intelligence"],
            },
        ],
        "metadata": exported["metadata"],
    }


def _export_summary(summary: ProtocolSummary) -> dict[str, Any]:
    return {
        "protocol_root": summary.protocol_root,
        "protocol_name": summary.protocol_name,
        "headline": summary.headline,
        "overview": summary.overview,
        "overall_risk_level": summary.overall_risk_level,
        "overall_risk_score": str(summary.overall_risk_score),
        "key_findings": list(summary.key_findings),
        "scan_coverage_pct": str(summary.scan_coverage_pct),
        "generated_at": summary.generated_at.isoformat(),
    }


def _export_posture(posture: ProtocolSecurityPosture) -> dict[str, Any]:
    return {
        "protocol_risk": _export_metric(posture.protocol_risk),
        "attack_surface": _export_metric(posture.attack_surface),
        "privilege_concentration": _export_metric(posture.privilege_concentration),
        "trust_boundaries": _export_metric(posture.trust_boundaries),
        "dependency_count": posture.dependency_count,
        "upgradeability": _export_metric(posture.upgradeability),
        "governance_maturity": _export_metric(posture.governance_maturity),
        "protocol_complexity": _export_metric(posture.protocol_complexity),
    }


def _export_metric(metric: Any) -> dict[str, Any]:
    return {
        "name": metric.name,
        "score": str(metric.score),
        "level": metric.level.value,
        "detail": metric.detail,
    }


def _export_recommendation(recommendation: ProtocolRecommendation) -> dict[str, Any]:
    return {
        "id": recommendation.id,
        "title": recommendation.title,
        "severity": recommendation.severity.value,
        "priority": recommendation.priority,
        "rationale": recommendation.rationale,
        "category": recommendation.category,
        "affected_nodes": list(recommendation.affected_nodes),
    }


def _export_intelligence(report: ProtocolExecutiveReport) -> dict[str, Any]:
    intelligence = report.intelligence
    return {
        "governance": _export_dataclass(intelligence.governance),
        "liquidity": _export_dataclass(intelligence.liquidity),
        "wallet": _export_dataclass(intelligence.wallet),
        "protocol": _export_dataclass(intelligence.protocol),
        "relationship": _export_dataclass(intelligence.relationship),
        "threat": _export_dataclass(intelligence.threat),
        "correlated_evidence": {
            "finding_count": intelligence.correlated_evidence.finding_count,
            "severities": list(intelligence.correlated_evidence.severities),
            "findings": [
                _export_dataclass(finding)
                for finding in intelligence.correlated_evidence.findings
            ],
        },
        "risk_evidence_count": len(intelligence.risk_evidence),
    }


def _export_dataclass(value: Any) -> dict[str, Any]:
    if hasattr(value, "__dataclass_fields__"):
        return {key: _normalize(getattr(value, key)) for key in value.__dataclass_fields__}
    return _normalize(value)


def _normalize(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, tuple):
        return [_normalize(item) for item in value]
    if isinstance(value, list):
        return [_normalize(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _normalize(item) for key, item in sorted(value.items())}
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def _json_default(value: Any) -> Any:
    normalized = _normalize(value)
    if normalized is value and not isinstance(value, (str, int, float, bool, type(None))):
        return str(value)
    return normalized
