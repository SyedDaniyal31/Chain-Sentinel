"""Rule-based rug-pull risk scoring from contract reconnaissance findings."""

from decimal import Decimal

from app.blockchain.risk.correlation.engine import RiskCorrelationEngine
from app.blockchain.risk.correlation.models import CorrelationResult
from app.blockchain.risk.evidence_builder import RiskEvidenceBuilder
from app.blockchain.risk.evidence_types import EvidenceCategory, EvidenceMetadataKey
from app.blockchain.risk.models import RiskEvidence
from app.blockchain.risk.scoring_weights import (
    CENTRAL_ADMIN_CONTRACT,
    CENTRAL_ADMIN_EOA,
    CENTRAL_ADMIN_MULTISIG,
    CENTRAL_ADMIN_TIMELOCK,
    CENTRAL_LOW_MAX,
    CENTRAL_MEDIUM_MAX,
    CENTRAL_OWNERSHIP_CAPABILITY,
    CENTRAL_UPGRADEABLE_UNKNOWN_ADMIN,
    CONFIDENCE_BYTECODE_CONFIRMED,
    CONFIDENCE_CLASSIFICATION,
    CONFIDENCE_DETECTION_BYTECODE,
    CONFIDENCE_DETECTION_HYBRID,
    CONFIDENCE_DETECTION_NONE,
    CONFIDENCE_DETECTION_SIMULATION,
    CONFIDENCE_DETECTION_SOURCE,
    CONFIDENCE_EOA_CONFIRMED,
    CONFIDENCE_LOW_MAX,
    CONFIDENCE_MEDIUM_MAX,
    CONFIDENCE_PROXY_RESOLVED,
    CONFIDENCE_PROXY_UNRESOLVED_PENALTY,
    CONFIDENCE_TRADE_SIMULATED,
    CONFIDENCE_VERIFIED_SOURCE,
    HIGH_TAX_BPS_THRESHOLD,
    LOW_LIQUIDITY_USD,
    LOW_MAX,
    MEDIUM_MAX,
    REASON_ADMIN_CONTRACT,
    REASON_ADMIN_EOA,
    REASON_ADMIN_MULTISIG,
    REASON_BLACKLIST_CAPABILITY,
    REASON_BLACKLIST_SELL_BLOCKING,
    REASON_CREATOR_OWNS_MAJORITY,
    REASON_EXCHANGE_FUNDED_DEPLOYER,
    REASON_FRESH_DEPLOYER,
    REASON_IMPLEMENTATION,
    REASON_LP_OWNER_IS_CREATOR,
    REASON_LOW_LIQUIDITY,
    REASON_MINT_CAPABILITY,
    REASON_NO_LIQUIDITY,
    REASON_NO_UPGRADE_SIGNALS,
    REASON_NOT_CONTRACT,
    REASON_OWNERSHIP_CAPABILITY,
    REASON_PAUSE_CAPABILITY,
    REASON_PROXYADMIN_OWNER,
    REASON_SIM_BUY_BLOCKED,
    REASON_SIM_HIGH_BUY_TAX,
    REASON_SIM_HIGH_SELL_TAX,
    REASON_SIM_SELL_BLOCKED,
    REASON_SINGLE_WALLET_LP,
    REASON_TORNADO_FUNDED_DEPLOYER,
    REASON_TREASURY_MULTISIG,
    REASON_TRADING_ENABLED_CONTROL,
    REASON_TRANSFER_TAX_CONTROL,
    REASON_UNLOCKED_LP,
    REASON_UPGRADEABLE,
    REASON_WALLET_KNOWN_SCAM,
    REASON_WHITELIST_CONTROL,
    SCORE_ADMIN_CONTRACT,
    SCORE_ADMIN_EOA,
    SCORE_ADMIN_MULTISIG,
    SCORE_ADMIN_TIMELOCK,
    SCORE_BLACKLIST_CAPABILITY,
    SCORE_BLACKLIST_SELL_BLOCKING,
    SCORE_CREATOR_OWNS_MAJORITY,
    SCORE_EXCHANGE_FUNDED_DEPLOYER,
    SCORE_FRESH_DEPLOYER,
    SCORE_IMPLEMENTATION,
    SCORE_LP_OWNER_IS_CREATOR,
    SCORE_LOW_LIQUIDITY,
    SCORE_MINT_CAPABILITY,
    SCORE_NO_LIQUIDITY,
    SCORE_OWNERSHIP_CAPABILITY,
    SCORE_PAUSE_CAPABILITY,
    SCORE_SIM_BUY_BLOCKED,
    SCORE_SIM_HIGH_BUY_TAX,
    SCORE_SIM_HIGH_SELL_TAX,
    SCORE_SIM_SELL_BLOCKED,
    SCORE_SINGLE_WALLET_LP,
    SCORE_TORNADO_FUNDED_DEPLOYER,
    SCORE_TRADING_ENABLED_CONTROL,
    SCORE_TRANSFER_TAX_CONTROL,
    SCORE_TREASURY_MULTISIG,
    SCORE_UNLOCKED_LP,
    SCORE_UPGRADEABLE,
    SCORE_WALLET_KNOWN_SCAM,
    SCORE_WHITELIST_CONTROL,
    THREAT_BLACKLIST,
    THREAT_BLACKLIST_SELL,
    THREAT_HIGH_MAX,
    THREAT_IMPLEMENTATION,
    THREAT_LOW_LIQUIDITY,
    THREAT_LOW_MAX,
    THREAT_MEDIUM_MAX,
    THREAT_MINT,
    THREAT_NO_LIQUIDITY,
    THREAT_OWNERSHIP,
    THREAT_PAUSE,
    THREAT_SIM_BUY_BLOCKED,
    THREAT_SIM_HIGH_BUY_TAX,
    THREAT_SIM_HIGH_SELL_TAX,
    THREAT_SIM_SELL_BLOCKED,
    THREAT_TRADING_ENABLED,
    THREAT_TRANSFER_TAX,
    THREAT_UNLOCKED_LP,
    THREAT_UPGRADEABLE,
    THREAT_WHITELIST,
    timelock_reason,
)
from app.models.enums import CentralizationLevel, ConfidenceLevel, RiskLevel, ThreatLevel
from app.schemas.risk import ContractRiskInput, RiskAssessment

__all__ = [
    "CENTRAL_ADMIN_CONTRACT",
    "CENTRAL_ADMIN_EOA",
    "CENTRAL_ADMIN_MULTISIG",
    "CENTRAL_ADMIN_TIMELOCK",
    "CENTRAL_LOW_MAX",
    "CENTRAL_MEDIUM_MAX",
    "CENTRAL_OWNERSHIP_CAPABILITY",
    "CENTRAL_UPGRADEABLE_UNKNOWN_ADMIN",
    "CONFIDENCE_BYTECODE_CONFIRMED",
    "CONFIDENCE_CLASSIFICATION",
    "CONFIDENCE_DETECTION_BYTECODE",
    "CONFIDENCE_DETECTION_HYBRID",
    "CONFIDENCE_DETECTION_NONE",
    "CONFIDENCE_DETECTION_SIMULATION",
    "CONFIDENCE_DETECTION_SOURCE",
    "CONFIDENCE_EOA_CONFIRMED",
    "CONFIDENCE_LOW_MAX",
    "CONFIDENCE_MEDIUM_MAX",
    "CONFIDENCE_PROXY_RESOLVED",
    "CONFIDENCE_PROXY_UNRESOLVED_PENALTY",
    "CONFIDENCE_TRADE_SIMULATED",
    "CONFIDENCE_VERIFIED_SOURCE",
    "HIGH_TAX_BPS_THRESHOLD",
    "LOW_LIQUIDITY_USD",
    "LOW_MAX",
    "MEDIUM_MAX",
    "REASON_ADMIN_CONTRACT",
    "REASON_ADMIN_EOA",
    "REASON_ADMIN_MULTISIG",
    "REASON_BLACKLIST_CAPABILITY",
    "REASON_BLACKLIST_SELL_BLOCKING",
    "REASON_CREATOR_OWNS_MAJORITY",
    "REASON_EXCHANGE_FUNDED_DEPLOYER",
    "REASON_FRESH_DEPLOYER",
    "REASON_IMPLEMENTATION",
    "REASON_LP_OWNER_IS_CREATOR",
    "REASON_LOW_LIQUIDITY",
    "REASON_MINT_CAPABILITY",
    "REASON_NO_LIQUIDITY",
    "REASON_NO_UPGRADE_SIGNALS",
    "REASON_NOT_CONTRACT",
    "REASON_OWNERSHIP_CAPABILITY",
    "REASON_PAUSE_CAPABILITY",
    "REASON_PROXYADMIN_OWNER",
    "REASON_SIM_BUY_BLOCKED",
    "REASON_SIM_HIGH_BUY_TAX",
    "REASON_SIM_HIGH_SELL_TAX",
    "REASON_SIM_SELL_BLOCKED",
    "REASON_SINGLE_WALLET_LP",
    "REASON_TORNADO_FUNDED_DEPLOYER",
    "REASON_TREASURY_MULTISIG",
    "REASON_TRADING_ENABLED_CONTROL",
    "REASON_TRANSFER_TAX_CONTROL",
    "REASON_UNLOCKED_LP",
    "REASON_UPGRADEABLE",
    "REASON_WALLET_KNOWN_SCAM",
    "REASON_WHITELIST_CONTROL",
    "RiskEngine",
    "SCORE_ADMIN_CONTRACT",
    "SCORE_ADMIN_EOA",
    "SCORE_ADMIN_MULTISIG",
    "SCORE_ADMIN_TIMELOCK",
    "SCORE_BLACKLIST_CAPABILITY",
    "SCORE_BLACKLIST_SELL_BLOCKING",
    "SCORE_CREATOR_OWNS_MAJORITY",
    "SCORE_EXCHANGE_FUNDED_DEPLOYER",
    "SCORE_FRESH_DEPLOYER",
    "SCORE_IMPLEMENTATION",
    "SCORE_LP_OWNER_IS_CREATOR",
    "SCORE_LOW_LIQUIDITY",
    "SCORE_MINT_CAPABILITY",
    "SCORE_NO_LIQUIDITY",
    "SCORE_OWNERSHIP_CAPABILITY",
    "SCORE_PAUSE_CAPABILITY",
    "SCORE_SIM_BUY_BLOCKED",
    "SCORE_SIM_HIGH_BUY_TAX",
    "SCORE_SIM_HIGH_SELL_TAX",
    "SCORE_SIM_SELL_BLOCKED",
    "SCORE_SINGLE_WALLET_LP",
    "SCORE_TORNADO_FUNDED_DEPLOYER",
    "SCORE_TRADING_ENABLED_CONTROL",
    "SCORE_TRANSFER_TAX_CONTROL",
    "SCORE_TREASURY_MULTISIG",
    "SCORE_UNLOCKED_LP",
    "SCORE_UPGRADEABLE",
    "SCORE_WALLET_KNOWN_SCAM",
    "SCORE_WHITELIST_CONTROL",
    "THREAT_BLACKLIST",
    "THREAT_BLACKLIST_SELL",
    "THREAT_HIGH_MAX",
    "THREAT_IMPLEMENTATION",
    "THREAT_LOW_LIQUIDITY",
    "THREAT_LOW_MAX",
    "THREAT_MEDIUM_MAX",
    "THREAT_MINT",
    "THREAT_NO_LIQUIDITY",
    "THREAT_OWNERSHIP",
    "THREAT_PAUSE",
    "THREAT_SIM_BUY_BLOCKED",
    "THREAT_SIM_HIGH_BUY_TAX",
    "THREAT_SIM_HIGH_SELL_TAX",
    "THREAT_SIM_SELL_BLOCKED",
    "THREAT_TRADING_ENABLED",
    "THREAT_TRANSFER_TAX",
    "THREAT_UNLOCKED_LP",
    "THREAT_UPGRADEABLE",
    "THREAT_WHITELIST",
    "timelock_reason",
]


class RiskEngine:
    """Converts unified risk evidence into actionable risk intelligence."""

    def __init__(
        self,
        evidence_builder: RiskEvidenceBuilder | None = None,
        correlation_engine: RiskCorrelationEngine | None = None,
    ) -> None:
        self._evidence_builder = evidence_builder or RiskEvidenceBuilder()
        self._correlation_engine = correlation_engine or RiskCorrelationEngine()

    def correlate(self, evidence: list[RiskEvidence]) -> CorrelationResult:
        """Run the correlation engine over normalized evidence."""
        return self._correlation_engine.correlate(evidence)

    def evaluate_contract_risk(self, findings: ContractRiskInput) -> RiskAssessment:
        """
        Score contract rug-pull risk from flattened analyzer findings.

        Preserves the legacy public API by adapting ContractRiskInput into evidence first.
        """
        evidence = self._evidence_builder.from_contract_risk_input(findings)
        return self.evaluate_from_evidence(evidence)

    def evaluate_from_evidence(self, evidence: list[RiskEvidence]) -> RiskAssessment:
        """Score contract rug-pull risk from normalized analyzer evidence."""
        if self._has_signal(evidence, "not_contract"):
            return RiskAssessment(
                risk_score=Decimal("0.00"),
                risk_level=RiskLevel.LOW,
                risk_reasons=[REASON_NOT_CONTRACT],
                threat_level=ThreatLevel.LOW,
                centralization_level=CentralizationLevel.LOW,
                confidence_level=self._confidence_for_eoa(),
            )

        correlation = self._correlation_engine.correlate(evidence)

        score = Decimal("0.00")
        reasons: list[str] = []
        for item in evidence:
            if item.category == EvidenceCategory.CONFIDENCE:
                continue
            if item.score != 0 or item.metadata.get(EvidenceMetadataKey.REASON_ONLY.value):
                reasons.append(item.reason)
            score += item.score

        for finding in correlation.findings:
            score += finding.score_delta

        if score > Decimal("100.00"):
            score = Decimal("100.00")
        if score < Decimal("0.00"):
            score = Decimal("0.00")

        if not reasons:
            reasons.append(REASON_NO_UPGRADE_SIGNALS)

        return RiskAssessment(
            risk_score=score,
            risk_level=self._score_to_level(score),
            risk_reasons=reasons,
            threat_level=self._evaluate_threat_level_from_evidence(evidence),
            centralization_level=self._evaluate_centralization_level_from_evidence(evidence),
            confidence_level=self._evaluate_confidence_level_from_evidence(evidence),
        )

    @staticmethod
    def _has_signal(evidence: list[RiskEvidence], signal: str) -> bool:
        key = EvidenceMetadataKey.SIGNAL.value
        return any(item.metadata.get(key) == signal for item in evidence)

    def _evaluate_threat_level_from_evidence(self, evidence: list[RiskEvidence]) -> ThreatLevel:
        """Score exploit mechanics from normalized evidence metadata."""
        if any(
            item.metadata.get(EvidenceMetadataKey.FORCE_THREAT_CRITICAL.value)
            for item in evidence
        ):
            return ThreatLevel.CRITICAL

        score = 0
        for item in evidence:
            threat_weight = item.metadata.get(EvidenceMetadataKey.THREAT_WEIGHT.value, 0)
            if isinstance(threat_weight, (int, float, Decimal)):
                score += int(threat_weight)

        if score > THREAT_HIGH_MAX:
            return ThreatLevel.CRITICAL
        if score > THREAT_MEDIUM_MAX:
            return ThreatLevel.HIGH
        if score > THREAT_LOW_MAX:
            return ThreatLevel.MEDIUM
        return ThreatLevel.LOW

    @staticmethod
    def _evaluate_centralization_level_from_evidence(
        evidence: list[RiskEvidence],
    ) -> CentralizationLevel:
        """Score governance concentration from normalized evidence metadata."""
        score = 0
        for item in evidence:
            central_weight = item.metadata.get(EvidenceMetadataKey.CENTRALIZATION_WEIGHT.value, 0)
            if isinstance(central_weight, (int, float, Decimal)):
                score += int(central_weight)

        if score > CENTRAL_MEDIUM_MAX:
            return CentralizationLevel.HIGH
        if score > CENTRAL_LOW_MAX:
            return CentralizationLevel.MEDIUM
        return CentralizationLevel.LOW

    @staticmethod
    def _evaluate_confidence_level_from_evidence(
        evidence: list[RiskEvidence],
    ) -> ConfidenceLevel:
        """Score how much evidence supports the overall assessment."""
        score = 0
        for item in evidence:
            confidence_weight = item.metadata.get(EvidenceMetadataKey.CONFIDENCE_WEIGHT.value, 0)
            if isinstance(confidence_weight, (int, float, Decimal)):
                score += int(confidence_weight)

        if score > CONFIDENCE_MEDIUM_MAX:
            return ConfidenceLevel.HIGH
        if score > CONFIDENCE_LOW_MAX:
            return ConfidenceLevel.MEDIUM
        return ConfidenceLevel.LOW

    @staticmethod
    def _score_to_level(score: Decimal) -> RiskLevel:
        if score <= LOW_MAX:
            return RiskLevel.LOW
        if score <= MEDIUM_MAX:
            return RiskLevel.MEDIUM
        return RiskLevel.HIGH

    @staticmethod
    def _confidence_for_eoa() -> ConfidenceLevel:
        """EOA classification via empty bytecode is reliable but narrow scope."""
        if CONFIDENCE_EOA_CONFIRMED > CONFIDENCE_MEDIUM_MAX:
            return ConfidenceLevel.HIGH
        if CONFIDENCE_EOA_CONFIRMED > CONFIDENCE_LOW_MAX:
            return ConfidenceLevel.MEDIUM
        return ConfidenceLevel.LOW
