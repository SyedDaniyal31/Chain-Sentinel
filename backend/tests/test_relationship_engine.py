"""Relationship engine unit tests (M6.3)."""

from app.blockchain.protocol.relationship_engine import merge_duplicate_wallet_relationships, normalize_relationships
from app.blockchain.protocol.relationship_models import (
    ArchitectureNodeType,
    ProtocolRelationshipCandidate,
    RelationshipType,
)


def test_normalize_relationships_deduplicates_and_sorts() -> None:
    candidates = [
        ProtocolRelationshipCandidate(
            source_id="contract:0x1",
            source_label="Target Contract",
            source_type=ArchitectureNodeType.CONTRACT,
            target_id="dex:uniswap",
            target_label="Uniswap V3 (pool)",
            target_type=ArchitectureNodeType.DEX,
            relationship_type=RelationshipType.TRADES_ON,
            confidence=80,
            detection_source="protocol_intelligence.dex",
        ),
        ProtocolRelationshipCandidate(
            source_id="contract:0x1",
            source_label="Target Contract",
            source_type=ArchitectureNodeType.CONTRACT,
            target_id="dex:uniswap",
            target_label="Uniswap V3 (pool)",
            target_type=ArchitectureNodeType.DEX,
            relationship_type=RelationshipType.TRADES_ON,
            confidence=90,
            detection_source="liquidity_intelligence.primary_dex",
        ),
    ]
    relationships = normalize_relationships(candidates)
    assert len(relationships) == 1
    assert relationships[0].confidence == 90
    assert relationships[0].detection_source == "liquidity_intelligence.primary_dex"


def test_merge_duplicate_wallet_relationships_keeps_best_confidence() -> None:
    from app.blockchain.protocol.relationship_models import ProtocolRelationship

    relationships = [
        ProtocolRelationship(
            source="Target Contract",
            target="Owner",
            relationship_type=RelationshipType.OWNED_BY,
            confidence=80,
            detection_source="wallet_intelligence.ownership",
        ),
        ProtocolRelationship(
            source="Target Contract",
            target="Owner",
            relationship_type=RelationshipType.OWNED_BY,
            confidence=88,
            detection_source="governance_intelligence.ownership",
        ),
    ]
    merged = merge_duplicate_wallet_relationships(relationships)
    assert len(merged) == 1
    assert merged[0].confidence == 88
