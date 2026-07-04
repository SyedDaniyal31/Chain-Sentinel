"""Evidence-weighted confidence computation for M6.1 protocol intelligence."""

from __future__ import annotations

from app.blockchain.protocol.models import ProtocolConfidenceScore, ProtocolDetectionBundle
from app.models.enums import ConfidenceLevel

HIGH_THRESHOLD = 70
MEDIUM_THRESHOLD = 40


def compute_confidence(bundle: ProtocolDetectionBundle) -> ProtocolConfidenceScore:
    """Compute a 0–100 confidence score from aggregated detector evidence."""
    if not _has_any_evidence(bundle):
        return ProtocolConfidenceScore(score=0, level=ConfidenceLevel.LOW.value)

    score = 0

    for item in bundle.standards:
        if not item.detected:
            continue
        score += 15 if item.confidence == "high" else 8

    for item in bundle.frameworks:
        if not item.detected:
            continue
        score += 12 if item.confidence == "high" else 6

    high_signal_count = sum(
        1
        for item in (*bundle.standards, *bundle.frameworks)
        if item.detected and item.confidence == "high"
    )
    if high_signal_count >= 2:
        score += 15

    if bundle.proxy and bundle.proxy.detected:
        score += 10 if bundle.proxy.confidence == "high" else 5

    score += min(25, len(bundle.integrations) * 5)
    score += min(30, len(bundle.detection_reasons) * 15)

    for dex in bundle.dexes:
        score += min(20, dex.confidence // 5)
    for loan in bundle.lending:
        score += min(20, loan.confidence // 5)
    for oracle in bundle.oracles:
        score += min(15, oracle.confidence // 6)
    for bridge in bundle.bridges:
        score += min(18, bridge.confidence // 6)
    for vault in bundle.vaults:
        score += min(18, vault.confidence // 6)
    for nft in bundle.nfts:
        score += min(15, nft.confidence // 7)
    for gov in bundle.governance:
        score += min(18, gov.confidence // 6)

    score = max(0, min(100, score))
    level = _score_to_level(score)
    return ProtocolConfidenceScore(score=score, level=level.value)


def resolve_confidence_level(bundle: ProtocolDetectionBundle) -> ConfidenceLevel:
    """Backward-compatible confidence level derived from the evidence engine."""
    return ConfidenceLevel(compute_confidence(bundle).level)


def _score_to_level(score: int) -> ConfidenceLevel:
    if score >= HIGH_THRESHOLD:
        return ConfidenceLevel.HIGH
    if score >= MEDIUM_THRESHOLD:
        return ConfidenceLevel.MEDIUM
    return ConfidenceLevel.LOW


def _has_any_evidence(bundle: ProtocolDetectionBundle) -> bool:
    return bool(
        bundle.detection_reasons
        or bundle.integrations
        or bundle.dexes
        or bundle.lending
        or bundle.oracles
        or bundle.bridges
        or bundle.vaults
        or bundle.nfts
        or bundle.governance
        or any(item.detected for item in bundle.standards)
        or any(item.detected for item in bundle.frameworks)
        or (bundle.proxy and bundle.proxy.detected)
    )
