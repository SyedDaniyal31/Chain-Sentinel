"""Cross-chain bridge protocol detection for M6.2 infrastructure intelligence."""

from __future__ import annotations

from dataclasses import dataclass

from app.blockchain.protocol.bridge_registry import match_bridge_deployments
from app.blockchain.protocol.defi_registry import source_contains_marker
from app.blockchain.protocol.models import BridgeDetectionResult, ProtocolDetectionContext

LZ_RECEIVE = bytes.fromhex("00167cde")
LZ_SEND = bytes.fromhex("c7c7f5b3")
ENDPOINT_ID = bytes.fromhex("2f54bf6e")

WORMHOLE_PUBLISH = bytes.fromhex("b8e6c081")
WORMHOLE_VERIFY = bytes.fromhex("6a761202")

HYPERLANE_DISPATCH = bytes.fromhex("5c3d5c12")
HYPERLANE_PROCESS = bytes.fromhex("3a5a4956")

AXELAR_CALL = bytes.fromhex("4cf5b852")
AXELAR_VALIDATE = bytes.fromhex("8f283970")

STARGATE_SWAP = bytes.fromhex("c4d66de8")
STARGATE_SEND = bytes.fromhex("f2b6777c")

CCTP_DEPOSIT = bytes.fromhex("6fd3504e")
CCTP_RECEIVE = bytes.fromhex("57ecfd28")


@dataclass(frozen=True, slots=True)
class BridgeSignatureProfile:
    name: str
    role: str
    selectors: tuple[bytes, ...]
    source_markers: tuple[str, ...]


BRIDGE_SIGNATURE_PROFILES: tuple[BridgeSignatureProfile, ...] = (
    BridgeSignatureProfile(
        name="LayerZero",
        role="endpoint",
        selectors=(LZ_RECEIVE, LZ_SEND, ENDPOINT_ID),
        source_markers=("LAYERZERO", "LZENDPOINT", "ILAYERZERO"),
    ),
    BridgeSignatureProfile(
        name="Wormhole",
        role="core",
        selectors=(WORMHOLE_PUBLISH, WORMHOLE_VERIFY),
        source_markers=("WORMHOLE", "IWORMHOLE", "PUBLISHMESSAGE"),
    ),
    BridgeSignatureProfile(
        name="Hyperlane",
        role="mailbox",
        selectors=(HYPERLANE_DISPATCH, HYPERLANE_PROCESS),
        source_markers=("HYPERLANE", "IMAILBOX", "DISPATCH"),
    ),
    BridgeSignatureProfile(
        name="Axelar",
        role="gateway",
        selectors=(AXELAR_CALL, AXELAR_VALIDATE),
        source_markers=("AXELAR", "IAXELAR", "GATEWAY"),
    ),
    BridgeSignatureProfile(
        name="Stargate",
        role="router",
        selectors=(STARGATE_SWAP, STARGATE_SEND),
        source_markers=("STARGATE", "LAYERZERO", "ISTARGATE"),
    ),
    BridgeSignatureProfile(
        name="Circle CCTP",
        role="messenger",
        selectors=(CCTP_DEPOSIT, CCTP_RECEIVE),
        source_markers=("CCTP", "TOKENMESSENGER", "CIRCLE"),
    ),
)


def detect_bridges(context: ProtocolDetectionContext) -> list[BridgeDetectionResult]:
    """Detect bridge protocol integrations from registry, bytecode, and source."""
    if not context.bytecode and not context.logic_bytecode:
        return []

    results: dict[tuple[str, str], BridgeDetectionResult] = {}
    bytecode = context.logic_bytecode or context.bytecode

    for deployment in match_bridge_deployments(context.chain_id, context.target_address):
        _upsert_result(
            results,
            BridgeDetectionResult(
                name=deployment.protocol,
                role=deployment.role,
                confidence=94,
            ),
        )

    for profile in BRIDGE_SIGNATURE_PROFILES:
        selector_hits = sum(1 for selector in profile.selectors if selector in bytecode)
        if selector_hits == 0 and not source_contains_marker(context.verified_source_code, profile.source_markers):
            continue

        source_boost = 12 if source_contains_marker(context.verified_source_code, profile.source_markers) else 0
        verified_boost = 5 if context.is_verified and source_boost == 0 else 0
        score = min(100, 40 + selector_hits * 18 + source_boost + verified_boost)

        _upsert_result(
            results,
            BridgeDetectionResult(name=profile.name, role=profile.role, confidence=score),
        )

    return sorted(results.values(), key=lambda item: item.confidence, reverse=True)


def _upsert_result(
    results: dict[tuple[str, str], BridgeDetectionResult],
    candidate: BridgeDetectionResult,
) -> None:
    key = (candidate.name, candidate.role)
    existing = results.get(key)
    if existing is None or candidate.confidence > existing.confidence:
        results[key] = candidate
