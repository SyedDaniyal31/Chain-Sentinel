"""Relationship inference rules registry for M6.3 cross-protocol intelligence."""

from __future__ import annotations

from dataclasses import dataclass

from app.blockchain.protocol.relationship_models import RelationshipType


@dataclass(frozen=True, slots=True)
class RelationshipRule:
    """Maps a detector category to a default relationship type."""

    category: str
    relationship_type: RelationshipType
    confidence_boost: int = 0


PROTOCOL_INTEGRATION_RULES: tuple[RelationshipRule, ...] = (
    RelationshipRule("dex", RelationshipType.TRADES_ON),
    RelationshipRule("lending", RelationshipType.INTEGRATES),
    RelationshipRule("oracle", RelationshipType.PRICES_WITH),
    RelationshipRule("bridge", RelationshipType.BRIDGES_WITH),
    RelationshipRule("vault", RelationshipType.USES),
    RelationshipRule("nft", RelationshipType.INTEGRATES),
    RelationshipRule("governance_protocol", RelationshipType.GOVERNED_BY),
    RelationshipRule("integration", RelationshipType.INTEGRATES),
)


GOVERNANCE_RULES: tuple[tuple[str, RelationshipType], ...] = (
    ("ownership", RelationshipType.OWNED_BY),
    ("timelock", RelationshipType.GOVERNED_BY),
    ("upgrade_authority", RelationshipType.UPGRADEABLE_BY),
    ("proxy_admin", RelationshipType.UPGRADEABLE_BY),
    ("implementation", RelationshipType.DEPENDS_ON),
    ("capability_controller", RelationshipType.GOVERNED_BY),
)


WALLET_RULES: tuple[tuple[str, RelationshipType], ...] = (
    ("deployer", RelationshipType.CREATED_BY),
    ("creator", RelationshipType.CREATED_BY),
    ("owner", RelationshipType.OWNED_BY),
    ("treasury", RelationshipType.SECURED_BY),
    ("proxy_admin", RelationshipType.UPGRADEABLE_BY),
)


LIQUIDITY_RULES: tuple[tuple[str, RelationshipType], ...] = (
    ("primary_dex", RelationshipType.TRADES_ON),
    ("liquidity_pool", RelationshipType.DEPENDS_ON),
)


def protocol_category_rule(category: str) -> RelationshipRule | None:
    for rule in PROTOCOL_INTEGRATION_RULES:
        if rule.category == category:
            return rule
    return None
