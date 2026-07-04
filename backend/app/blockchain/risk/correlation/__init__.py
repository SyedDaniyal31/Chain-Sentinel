"""Risk evidence correlation layer (M7.2)."""

from app.blockchain.risk.correlation.engine import RiskCorrelationEngine
from app.blockchain.risk.correlation.models import (
    CorrelatedRiskFinding,
    CorrelationImpact,
    CorrelationLikelihood,
    CorrelationResult,
    CorrelationRule,
)
from app.blockchain.risk.correlation.registry import CorrelationRuleRegistry, get_default_registry

__all__ = [
    "CorrelatedRiskFinding",
    "CorrelationImpact",
    "CorrelationLikelihood",
    "CorrelationResult",
    "CorrelationRule",
    "CorrelationRuleRegistry",
    "RiskCorrelationEngine",
    "get_default_registry",
]
