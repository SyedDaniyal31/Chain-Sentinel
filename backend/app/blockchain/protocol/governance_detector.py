"""Governance protocol detection for M6.2 infrastructure intelligence."""

from __future__ import annotations

from dataclasses import dataclass

from app.blockchain.protocol.defi_registry import source_contains_marker
from app.blockchain.protocol.governance_registry import match_governance_deployments
from app.blockchain.protocol.models import GovernanceDetectionResult, ProtocolDetectionContext

GOVERNOR_PROPOSE = bytes.fromhex("0121a88c")
GOVERNOR_CAST_VOTE = bytes.fromhex("56781388")
GOVERNOR_QUEUE = bytes.fromhex("160eed98")
GOVERNOR_EXECUTE = bytes.fromhex("fe0d94c1")
TIMELOCK_SCHEDULE = bytes.fromhex("f2a0ba21")
SAFE_GET_VOTES = bytes.fromhex("3a46b1a8")


@dataclass(frozen=True, slots=True)
class GovernanceSignatureProfile:
    name: str
    selectors: tuple[bytes, ...]
    source_markers: tuple[str, ...]


GOVERNANCE_SIGNATURE_PROFILES: tuple[GovernanceSignatureProfile, ...] = (
    GovernanceSignatureProfile(
        name="Governor Bravo",
        selectors=(GOVERNOR_PROPOSE, GOVERNOR_CAST_VOTE, GOVERNOR_QUEUE, GOVERNOR_EXECUTE),
        source_markers=("GOVERNORBRAVO", "IGovernorBravo", "BRAVO"),
    ),
    GovernanceSignatureProfile(
        name="OpenZeppelin Governor",
        selectors=(GOVERNOR_PROPOSE, GOVERNOR_CAST_VOTE, GOVERNOR_QUEUE),
        source_markers=("GOVERNOR", "IGovernor", "OPENZEPPELIN GOVERNOR"),
    ),
    GovernanceSignatureProfile(
        name="Safe Governor",
        selectors=(SAFE_GET_VOTES, GOVERNOR_CAST_VOTE),
        source_markers=("SAFE GOVERNOR", "GNOSIS GOVERNOR", "ISafeGovernor"),
    ),
    GovernanceSignatureProfile(
        name="Compound Governor",
        selectors=(GOVERNOR_PROPOSE, GOVERNOR_CAST_VOTE, GOVERNOR_EXECUTE),
        source_markers=("COMPOUND GOVERNOR", "ICOMPGOVERNOR", "COMPOUNDGOVERNOR"),
    ),
    GovernanceSignatureProfile(
        name="Timelock Governor",
        selectors=(TIMELOCK_SCHEDULE, GOVERNOR_EXECUTE),
        source_markers=("TIMELOCKCONTROLLER", "ITimeLock", "TIMELOCK GOVERNOR"),
    ),
)


def detect_governance(context: ProtocolDetectionContext) -> list[GovernanceDetectionResult]:
    """Detect governance protocol integrations from registry, bytecode, and source."""
    if not context.bytecode and not context.logic_bytecode:
        return []

    results: dict[str, GovernanceDetectionResult] = {}
    bytecode = context.logic_bytecode or context.bytecode

    for deployment in match_governance_deployments(context.chain_id, context.target_address):
        _upsert_result(
            results,
            GovernanceDetectionResult(name=deployment.protocol, confidence=92),
        )

    for profile in GOVERNANCE_SIGNATURE_PROFILES:
        selector_hits = sum(1 for selector in profile.selectors if selector in bytecode)
        if selector_hits == 0 and not source_contains_marker(context.verified_source_code, profile.source_markers):
            continue

        source_boost = 12 if source_contains_marker(context.verified_source_code, profile.source_markers) else 0
        verified_boost = 5 if context.is_verified and source_boost == 0 else 0
        score = min(100, 38 + selector_hits * 14 + source_boost + verified_boost)

        _upsert_result(
            results,
            GovernanceDetectionResult(name=profile.name, confidence=score),
        )

    return sorted(results.values(), key=lambda item: item.confidence, reverse=True)


def _upsert_result(
    results: dict[str, GovernanceDetectionResult],
    candidate: GovernanceDetectionResult,
) -> None:
    existing = results.get(candidate.name)
    if existing is None or candidate.confidence > existing.confidence:
        results[candidate.name] = candidate
