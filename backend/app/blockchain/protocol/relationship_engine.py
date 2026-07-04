"""Relationship normalization and confidence scoring engine (M6.3)."""

from __future__ import annotations

from app.blockchain.protocol.relationship_models import (
    ProtocolRelationship,
    ProtocolRelationshipCandidate,
)


def normalize_relationships(
    candidates: list[ProtocolRelationshipCandidate],
) -> list[ProtocolRelationship]:
    """Deduplicate and rank relationship candidates into API-ready edges."""
    merged: dict[tuple[str, str, str], ProtocolRelationship] = {}

    for candidate in candidates:
        key = (candidate.source_id, candidate.target_id, candidate.relationship_type.value)
        relationship = ProtocolRelationship(
            source=candidate.source_label,
            target=candidate.target_label,
            relationship_type=candidate.relationship_type,
            confidence=max(0, min(100, candidate.confidence)),
            detection_source=candidate.detection_source,
        )
        existing = merged.get(key)
        if existing is None or relationship.confidence > existing.confidence:
            merged[key] = relationship

    return sorted(
        merged.values(),
        key=lambda item: (item.confidence, item.source, item.target),
        reverse=True,
    )


def merge_duplicate_wallet_relationships(
    relationships: list[ProtocolRelationship],
) -> list[ProtocolRelationship]:
    """Prefer higher-confidence edges when multiple wallet roles collapse to one label."""
    best_by_pair: dict[tuple[str, str, str], ProtocolRelationship] = {}
    for relationship in relationships:
        key = (
            relationship.source,
            relationship.target,
            relationship.relationship_type.value,
        )
        existing = best_by_pair.get(key)
        if existing is None or relationship.confidence > existing.confidence:
            best_by_pair[key] = relationship
    return sorted(best_by_pair.values(), key=lambda item: item.confidence, reverse=True)
