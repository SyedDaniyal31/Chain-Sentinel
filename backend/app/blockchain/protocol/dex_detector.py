"""DEX protocol detection for M6.1 DeFi protocol intelligence."""

from __future__ import annotations

from dataclasses import dataclass

from app.blockchain.protocol.defi_registry import match_deployments, source_contains_marker
from app.blockchain.protocol.models import DexDetectionResult, ProtocolDetectionContext

# Uniswap V2 / SushiSwap / PancakeSwap / Aerodrome (V2-compatible)
V2_GET_RESERVES = bytes.fromhex("0902f1ac")
V2_SWAP = bytes.fromhex("022c0d9f")
V2_FACTORY_GET_PAIR = bytes.fromhex("e6a43905")

# Uniswap V3
V3_SLOT0 = bytes.fromhex("3850c7bd")
V3_SWAP = bytes.fromhex("128acb08")
V3_FACTORY_GET_POOL = bytes.fromhex("1698ee82")

# Curve
CURVE_EXCHANGE = bytes.fromhex("3df02124")
CURVE_GET_VIRTUAL_PRICE = bytes.fromhex("bb7b8b80")

# Balancer V2
BALANCER_GET_POOL_ID = bytes.fromhex("38cc4831")
BALANCER_ON_SWAP = bytes.fromhex("52bbbe29")


@dataclass(frozen=True, slots=True)
class DexSignatureProfile:
    """Bytecode/source fingerprint for a named DEX."""

    name: str
    roles: tuple[str, ...]
    selectors: tuple[bytes, ...]
    source_markers: tuple[str, ...] = ()


DEX_SIGNATURE_PROFILES: tuple[DexSignatureProfile, ...] = (
    DexSignatureProfile(
        name="Uniswap V2",
        roles=("pool", "factory"),
        selectors=(V2_GET_RESERVES, V2_SWAP),
        source_markers=("UNISWAPV2", "UNISWAP V2", "IUNISWAPV2PAIR"),
    ),
    DexSignatureProfile(
        name="Uniswap V3",
        roles=("pool", "factory"),
        selectors=(V3_SLOT0, V3_SWAP),
        source_markers=("UNISWAPV3", "UNISWAP V3", "IUNISWAPV3POOL"),
    ),
    DexSignatureProfile(
        name="SushiSwap",
        roles=("pool", "factory"),
        selectors=(V2_GET_RESERVES, V2_SWAP),
        source_markers=("SUSHISWAP", "UNISWAPV2", "ISUSHISWAP"),
    ),
    DexSignatureProfile(
        name="PancakeSwap",
        roles=("pool", "factory"),
        selectors=(V2_GET_RESERVES, V2_SWAP),
        source_markers=("PANCAKESWAP", "PANCAKE", "IPANCAKE"),
    ),
    DexSignatureProfile(
        name="Curve",
        roles=("pool", "router"),
        selectors=(CURVE_EXCHANGE, CURVE_GET_VIRTUAL_PRICE),
        source_markers=("CURVE", "STABLESWAP", "CRYPTOSWAP"),
    ),
    DexSignatureProfile(
        name="Balancer",
        roles=("pool", "vault"),
        selectors=(BALANCER_GET_POOL_ID, BALANCER_ON_SWAP),
        source_markers=("BALANCER", "VAULT", "IBALANCERVAULT"),
    ),
    DexSignatureProfile(
        name="Aerodrome",
        roles=("pool", "factory", "router"),
        selectors=(V2_GET_RESERVES, V2_SWAP),
        source_markers=("AERODROME", "VELODROME", "IAERODROMEPAIR"),
    ),
)


def detect_dexes(context: ProtocolDetectionContext) -> list[DexDetectionResult]:
    """
    Detect DEX protocol integrations from registry deployments, bytecode, and source.

    Returns structured results independent of other detectors.
    """
    if not context.bytecode and not context.logic_bytecode:
        return []

    results: dict[tuple[str, str], DexDetectionResult] = {}
    bytecode = context.logic_bytecode or context.bytecode

    for deployment in match_deployments(context.chain_id, context.target_address):
        if deployment.protocol not in {profile.name for profile in DEX_SIGNATURE_PROFILES}:
            continue
        _upsert_result(
            results,
            DexDetectionResult(
                name=deployment.protocol,
                role=deployment.role,
                confidence=95,
            ),
        )

    for profile in DEX_SIGNATURE_PROFILES:
        selector_hits = sum(1 for selector in profile.selectors if selector in bytecode)
        if selector_hits == 0:
            continue

        source_boost = 10 if source_contains_marker(context.verified_source_code, profile.source_markers) else 0
        verified_boost = 5 if context.is_verified and source_boost == 0 else 0
        base_score = 45 + (selector_hits * 15) + source_boost + verified_boost
        role = profile.roles[0] if selector_hits >= len(profile.selectors) else profile.roles[-1]
        score = min(100, base_score)

        _upsert_result(
            results,
            DexDetectionResult(name=profile.name, role=role, confidence=score),
        )

        if V2_FACTORY_GET_PAIR in bytecode or V3_FACTORY_GET_POOL in bytecode:
            factory_role = "factory"
            _upsert_result(
                results,
                DexDetectionResult(
                    name=profile.name,
                    role=factory_role,
                    confidence=min(100, score - 5),
                ),
            )

    return sorted(results.values(), key=lambda item: item.confidence, reverse=True)


def _upsert_result(
    results: dict[tuple[str, str], DexDetectionResult],
    candidate: DexDetectionResult,
) -> None:
    key = (candidate.name, candidate.role)
    existing = results.get(key)
    if existing is None or candidate.confidence > existing.confidence:
        results[key] = candidate
