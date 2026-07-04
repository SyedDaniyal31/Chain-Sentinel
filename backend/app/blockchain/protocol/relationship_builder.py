"""Relationship candidate builder for M6.3 cross-protocol intelligence."""

from __future__ import annotations

from app.blockchain.protocol.relationship_models import (
    ArchitectureNodeType,
    ProtocolRelationshipCandidate,
    RelationshipAnalysisContext,
    RelationshipType,
)
from app.blockchain.protocol.relationship_registry import protocol_category_rule


def build_relationship_candidates(context: RelationshipAnalysisContext) -> list[ProtocolRelationshipCandidate]:
    """Build raw relationship candidates from all intelligence inputs."""
    contract_id = _node_id("contract", context.target_address)
    contract_label = "Target Contract"
    candidates: list[ProtocolRelationshipCandidate] = []

    candidates.extend(_protocol_integration_candidates(context, contract_id, contract_label))
    candidates.extend(_governance_candidates(context, contract_id, contract_label))
    candidates.extend(_wallet_candidates(context, contract_id, contract_label))
    candidates.extend(_liquidity_candidates(context, contract_id, contract_label))
    candidates.extend(_proxy_candidates(context, contract_id, contract_label))
    candidates.extend(_capability_candidates(context, contract_id, contract_label))
    candidates.extend(_source_candidates(context, contract_id, contract_label))

    return candidates


def _protocol_integration_candidates(
    context: RelationshipAnalysisContext,
    contract_id: str,
    contract_label: str,
) -> list[ProtocolRelationshipCandidate]:
    candidates: list[ProtocolRelationshipCandidate] = []

    category_items = (
        ("dex", context.dexes, ArchitectureNodeType.DEX),
        ("lending", context.lending, ArchitectureNodeType.PROTOCOL),
        ("oracle", context.oracles, ArchitectureNodeType.ORACLE),
        ("bridge", context.bridges, ArchitectureNodeType.BRIDGE),
        ("vault", context.vaults, ArchitectureNodeType.VAULT),
        ("governance_protocol", context.governance_protocols, ArchitectureNodeType.GOVERNANCE),
    )

    for category, items, node_type in category_items:
        rule = protocol_category_rule(category)
        if rule is None:
            continue
        for item in items:
            name = str(item.get("name") or item.get("standard") or "unknown")
            role = item.get("role") or item.get("type") or item.get("marketplace") or ""
            label = f"{name} ({role})" if role else name
            confidence = int(item.get("confidence") or 70)
            candidates.append(
                ProtocolRelationshipCandidate(
                    source_id=contract_id,
                    source_label=contract_label,
                    source_type=ArchitectureNodeType.CONTRACT,
                    target_id=_node_id(category, name.lower()),
                    target_label=label,
                    target_type=node_type,
                    relationship_type=rule.relationship_type,
                    confidence=min(100, confidence + rule.confidence_boost),
                    detection_source=f"protocol_intelligence.{category}",
                )
            )

    for integration in context.integrations:
        candidates.append(
            ProtocolRelationshipCandidate(
                source_id=contract_id,
                source_label=contract_label,
                source_type=ArchitectureNodeType.CONTRACT,
                target_id=_node_id("integration", integration.lower()),
                target_label=integration,
                target_type=ArchitectureNodeType.PROTOCOL,
                relationship_type=RelationshipType.INTEGRATES,
                confidence=75,
                detection_source="protocol_intelligence.integrations",
            )
        )

    for nft in context.nfts:
        standard = str(nft.get("standard") or "NFT")
        marketplace = str(nft.get("marketplace") or "")
        label = f"{standard} · {marketplace}" if marketplace else standard
        candidates.append(
            ProtocolRelationshipCandidate(
                source_id=contract_id,
                source_label=contract_label,
                source_type=ArchitectureNodeType.CONTRACT,
                target_id=_node_id("nft", f"{standard}-{marketplace}".lower()),
                target_label=label,
                target_type=ArchitectureNodeType.PROTOCOL,
                relationship_type=RelationshipType.INTEGRATES,
                confidence=int(nft.get("confidence") or 70),
                detection_source="protocol_intelligence.nfts",
            )
        )

    return candidates


def _governance_candidates(
    context: RelationshipAnalysisContext,
    contract_id: str,
    contract_label: str,
) -> list[ProtocolRelationshipCandidate]:
    candidates: list[ProtocolRelationshipCandidate] = []

    if context.governance_ownership_address and not context.governance_ownership_renounced:
        candidates.append(
            ProtocolRelationshipCandidate(
                source_id=contract_id,
                source_label=contract_label,
                source_type=ArchitectureNodeType.CONTRACT,
                target_id=_node_id("wallet", context.governance_ownership_address),
                target_label="Governance Owner",
                target_type=ArchitectureNodeType.WALLET,
                target_address=context.governance_ownership_address,
                relationship_type=RelationshipType.OWNED_BY,
                confidence=88,
                detection_source="governance_intelligence.ownership",
            )
        )

    if context.has_timelock:
        candidates.append(
            ProtocolRelationshipCandidate(
                source_id=contract_id,
                source_label=contract_label,
                source_type=ArchitectureNodeType.CONTRACT,
                target_id=_node_id("governance", "timelock"),
                target_label="Timelock Controller",
                target_type=ArchitectureNodeType.GOVERNANCE,
                relationship_type=RelationshipType.GOVERNED_BY,
                confidence=85,
                detection_source="governance_intelligence.timelock",
            )
        )

    if context.upgrade_authority and context.upgrade_authority not in {"none", "unknown"}:
        candidates.append(
            ProtocolRelationshipCandidate(
                source_id=contract_id,
                source_label=contract_label,
                source_type=ArchitectureNodeType.CONTRACT,
                target_id=_node_id("governance", context.upgrade_authority),
                target_label=f"Upgrade Authority ({context.upgrade_authority})",
                target_type=ArchitectureNodeType.GOVERNANCE,
                relationship_type=RelationshipType.UPGRADEABLE_BY,
                confidence=82,
                detection_source="governance_intelligence.upgrade_authority",
            )
        )

    if context.governance_type and context.governance_type not in {"none", "unknown"}:
        candidates.append(
            ProtocolRelationshipCandidate(
                source_id=contract_id,
                source_label=contract_label,
                source_type=ArchitectureNodeType.CONTRACT,
                target_id=_node_id("governance", context.governance_type),
                target_label=f"Governance ({context.governance_type})",
                target_type=ArchitectureNodeType.GOVERNANCE,
                relationship_type=RelationshipType.GOVERNED_BY,
                confidence=80,
                detection_source="governance_intelligence.governance_type",
            )
        )

    return candidates


def _wallet_candidates(
    context: RelationshipAnalysisContext,
    contract_id: str,
    contract_label: str,
) -> list[ProtocolRelationshipCandidate]:
    candidates: list[ProtocolRelationshipCandidate] = []

    wallet_links = (
        (context.wallet_deployer, "Deployer", RelationshipType.CREATED_BY),
        (context.wallet_creator, "Creator", RelationshipType.CREATED_BY),
        (context.wallet_owner, "Owner", RelationshipType.OWNED_BY),
        (context.wallet_treasury, "Treasury", RelationshipType.SECURED_BY),
        (context.wallet_proxy_admin, "Proxy Admin", RelationshipType.UPGRADEABLE_BY),
    )

    for address, label, relationship_type in wallet_links:
        if not address:
            continue
        candidates.append(
            ProtocolRelationshipCandidate(
                source_id=contract_id,
                source_label=contract_label,
                source_type=ArchitectureNodeType.CONTRACT,
                target_id=_node_id("wallet", address),
                target_label=label,
                target_type=ArchitectureNodeType.WALLET,
                target_address=address,
                relationship_type=relationship_type,
                confidence=86,
                detection_source="wallet_intelligence.ownership",
            )
        )

    return candidates


def _liquidity_candidates(
    context: RelationshipAnalysisContext,
    contract_id: str,
    contract_label: str,
) -> list[ProtocolRelationshipCandidate]:
    if not context.liquidity_has_liquidity:
        return []

    candidates: list[ProtocolRelationshipCandidate] = []

    if context.liquidity_primary_dex:
        candidates.append(
            ProtocolRelationshipCandidate(
                source_id=contract_id,
                source_label=contract_label,
                source_type=ArchitectureNodeType.CONTRACT,
                target_id=_node_id("dex", context.liquidity_primary_dex.lower()),
                target_label=context.liquidity_primary_dex,
                target_type=ArchitectureNodeType.DEX,
                relationship_type=RelationshipType.TRADES_ON,
                confidence=84,
                detection_source="liquidity_intelligence.primary_dex",
            )
        )

    if context.liquidity_pair_address:
        candidates.append(
            ProtocolRelationshipCandidate(
                source_id=contract_id,
                source_label=contract_label,
                source_type=ArchitectureNodeType.CONTRACT,
                target_id=_node_id("liquidity", context.liquidity_pair_address),
                target_label="Primary Liquidity Pool",
                target_type=ArchitectureNodeType.LIQUIDITY,
                target_address=context.liquidity_pair_address,
                relationship_type=RelationshipType.DEPENDS_ON,
                confidence=83,
                detection_source="liquidity_intelligence.pair_address",
            )
        )

    return candidates


def _proxy_candidates(
    context: RelationshipAnalysisContext,
    contract_id: str,
    contract_label: str,
) -> list[ProtocolRelationshipCandidate]:
    candidates: list[ProtocolRelationshipCandidate] = []

    if context.implementation_address:
        candidates.append(
            ProtocolRelationshipCandidate(
                source_id=contract_id,
                source_label=contract_label,
                source_type=ArchitectureNodeType.CONTRACT,
                target_id=_node_id("implementation", context.implementation_address),
                target_label="Implementation",
                target_type=ArchitectureNodeType.IMPLEMENTATION,
                target_address=context.implementation_address,
                relationship_type=RelationshipType.DEPENDS_ON,
                confidence=90,
                detection_source="protocol_intelligence.proxy",
            )
        )

    if context.is_upgradeable and context.admin_address:
        candidates.append(
            ProtocolRelationshipCandidate(
                source_id=contract_id,
                source_label=contract_label,
                source_type=ArchitectureNodeType.CONTRACT,
                target_id=_node_id("wallet", context.admin_address),
                target_label="Proxy Admin",
                target_type=ArchitectureNodeType.WALLET,
                target_address=context.admin_address,
                relationship_type=RelationshipType.UPGRADEABLE_BY,
                confidence=87,
                detection_source="protocol_intelligence.proxy_admin",
            )
        )

    return candidates


def _capability_candidates(
    context: RelationshipAnalysisContext,
    contract_id: str,
    contract_label: str,
) -> list[ProtocolRelationshipCandidate]:
    candidates: list[ProtocolRelationshipCandidate] = []
    for capability_name, controller in context.capability_controllers:
        candidates.append(
            ProtocolRelationshipCandidate(
                source_id=contract_id,
                source_label=contract_label,
                source_type=ArchitectureNodeType.CONTRACT,
                target_id=_node_id("wallet", controller),
                target_label=f"{capability_name} Controller",
                target_type=ArchitectureNodeType.WALLET,
                target_address=controller,
                relationship_type=RelationshipType.GOVERNED_BY,
                confidence=78,
                detection_source="capability_intelligence.controller",
            )
        )
    return candidates


def _source_candidates(
    context: RelationshipAnalysisContext,
    contract_id: str,
    contract_label: str,
) -> list[ProtocolRelationshipCandidate]:
    if not context.honeypot_is_suspected:
        return []
    return [
        ProtocolRelationshipCandidate(
            source_id=contract_id,
            source_label=contract_label,
            source_type=ArchitectureNodeType.CONTRACT,
            target_id=_node_id("risk", "honeypot_controls"),
            target_label="Honeypot Controls",
            target_type=ArchitectureNodeType.PROTOCOL,
            relationship_type=RelationshipType.SECURED_BY,
            confidence=70,
            detection_source="honeypot_intelligence.summary",
        )
    ]


def _node_id(prefix: str, value: str) -> str:
    normalized = value.lower().replace(" ", "_")
    return f"{prefix}:{normalized}"
