"""Relationship builder unit tests (M6.3)."""

from app.blockchain.protocol.relationship_builder import build_relationship_candidates
from app.blockchain.protocol.relationship_models import RelationshipAnalysisContext, RelationshipType


def _base_context(**overrides) -> RelationshipAnalysisContext:
    base = RelationshipAnalysisContext(
        target_address="0x742d35cc6634c0532925a3b844bc9e7595f0beb0",
        protocol_family="dex",
        protocol_name="uniswap_v3_pool",
    )
    for key, value in overrides.items():
        setattr(base, key, value)
    return base


def test_build_relationship_candidates_from_dex_protocol() -> None:
    context = _base_context(
        dexes=[{"name": "Uniswap V3", "role": "pool", "confidence": 90}],
    )
    candidates = build_relationship_candidates(context)
    assert any(
        candidate.relationship_type == RelationshipType.TRADES_ON
        and candidate.target_label.startswith("Uniswap V3")
        for candidate in candidates
    )


def test_build_relationship_candidates_from_oracle_and_bridge() -> None:
    context = _base_context(
        oracles=[{"name": "Chainlink", "confidence": 88}],
        bridges=[{"name": "LayerZero", "role": "endpoint", "confidence": 94}],
    )
    candidates = build_relationship_candidates(context)
    assert any(candidate.relationship_type == RelationshipType.PRICES_WITH for candidate in candidates)
    assert any(candidate.relationship_type == RelationshipType.BRIDGES_WITH for candidate in candidates)


def test_build_relationship_candidates_from_governance_and_wallet() -> None:
    context = _base_context(
        governance_ownership_address="0x1234567890123456789012345678901234567890",
        has_timelock=True,
        wallet_deployer="0xabcdefabcdefabcdefabcdefabcdefabcdefabcd",
    )
    candidates = build_relationship_candidates(context)
    assert any(candidate.relationship_type == RelationshipType.OWNED_BY for candidate in candidates)
    assert any(candidate.relationship_type == RelationshipType.GOVERNED_BY for candidate in candidates)
    assert any(candidate.relationship_type == RelationshipType.CREATED_BY for candidate in candidates)


def test_build_relationship_candidates_from_liquidity() -> None:
    context = _base_context(
        liquidity_has_liquidity=True,
        liquidity_primary_dex="uniswap",
        liquidity_pair_address="0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    )
    candidates = build_relationship_candidates(context)
    assert any(candidate.relationship_type == RelationshipType.TRADES_ON for candidate in candidates)
    assert any(candidate.relationship_type == RelationshipType.DEPENDS_ON for candidate in candidates)
