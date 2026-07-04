"""Privileged entity analysis for M6.4 threat surface intelligence."""

from __future__ import annotations

from app.blockchain.security.threat_models import PrivilegedEntity, PrivilegedEntityType, ThreatSurfaceContext


def analyze_privileged_entities(context: ThreatSurfaceContext) -> list[PrivilegedEntity]:
    """Detect privileged entities with elevated control over the target contract."""
    entities: dict[tuple[str, str], PrivilegedEntity] = {}

    if context.wallet_owner and not context.governance_ownership_renounced:
        _upsert(
            entities,
            PrivilegedEntity(
                entity_type=PrivilegedEntityType.OWNER,
                label="Owner",
                confidence=88,
                detection_source="wallet_intelligence.owner",
                address=context.wallet_owner,
            ),
        )

    if context.governance_ownership_address and not context.governance_ownership_renounced:
        _upsert(
            entities,
            PrivilegedEntity(
                entity_type=PrivilegedEntityType.OWNER,
                label="Governance Owner",
                confidence=86,
                detection_source="governance_intelligence.ownership",
                address=context.governance_ownership_address,
            ),
        )

    if context.admin_address and context.is_upgradeable:
        _upsert(
            entities,
            PrivilegedEntity(
                entity_type=PrivilegedEntityType.PROXY_ADMIN,
                label="Proxy Admin",
                confidence=90,
                detection_source="protocol_intelligence.proxy_admin",
                address=context.admin_address,
            ),
        )

    if context.has_timelock:
        _upsert(
            entities,
            PrivilegedEntity(
                entity_type=PrivilegedEntityType.TIMELOCK,
                label="Timelock",
                confidence=85,
                detection_source="governance_intelligence.timelock",
            ),
        )

    for gov in context.governance_protocols:
        name = str(gov.get("name") or "Governor")
        entity_type = PrivilegedEntityType.GOVERNOR
        if "safe" in name.lower():
            entity_type = PrivilegedEntityType.SAFE
        elif "dao" in name.lower() or "compound" in name.lower():
            entity_type = PrivilegedEntityType.DAO
        _upsert(
            entities,
            PrivilegedEntity(
                entity_type=entity_type,
                label=name,
                confidence=int(gov.get("confidence") or 82),
                detection_source="protocol_intelligence.governance",
            ),
        )

    if context.treasury_is_multisig:
        _upsert(
            entities,
            PrivilegedEntity(
                entity_type=PrivilegedEntityType.MULTISIG,
                label="Treasury Multisig",
                confidence=88,
                detection_source="wallet_intelligence.treasury_multisig",
                address=context.wallet_treasury,
            ),
        )
    elif context.wallet_treasury:
        _upsert(
            entities,
            PrivilegedEntity(
                entity_type=PrivilegedEntityType.SAFE if context.treasury_is_multisig else PrivilegedEntityType.MULTISIG,
                label="Treasury",
                confidence=80,
                detection_source="wallet_intelligence.treasury",
                address=context.wallet_treasury,
            ),
        )

    for bridge in context.bridges:
        if bridge.get("role") in {"endpoint", "messenger", "router"}:
            _upsert(
                entities,
                PrivilegedEntity(
                    entity_type=PrivilegedEntityType.BRIDGE_RELAYER,
                    label=f"{bridge.get('name')} Relayer",
                    confidence=int(bridge.get("confidence") or 78),
                    detection_source="protocol_intelligence.bridges",
                ),
            )

    for oracle in context.oracles:
        _upsert(
            entities,
            PrivilegedEntity(
                entity_type=PrivilegedEntityType.ORACLE_ADMIN,
                label=f"{oracle.get('name')} Admin",
                confidence=int(oracle.get("confidence") or 75),
                detection_source="protocol_intelligence.oracles",
            ),
        )

    for capability_name, controller in context.capability_controllers:
        _upsert(
            entities,
            PrivilegedEntity(
                entity_type=PrivilegedEntityType.CAPABILITY_CONTROLLER,
                label=f"{capability_name} Controller",
                confidence=78,
                detection_source="capability_intelligence.controller",
                address=controller,
            ),
        )

    return sorted(entities.values(), key=lambda item: item.confidence, reverse=True)


def _upsert(
    entities: dict[tuple[str, str], PrivilegedEntity],
    candidate: PrivilegedEntity,
) -> None:
    key = (candidate.entity_type.value, (candidate.address or candidate.label).lower())
    existing = entities.get(key)
    if existing is None or candidate.confidence > existing.confidence:
        entities[key] = candidate
