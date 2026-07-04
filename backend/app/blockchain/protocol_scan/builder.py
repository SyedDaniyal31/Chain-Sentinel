"""Protocol discovery result builder (M8.1)."""

from __future__ import annotations

from app.blockchain.protocol_scan.models import (
    ProtocolContract,
    ProtocolDiscoveryResult,
    ProtocolRelationship,
    ProtocolRole,
)


class ProtocolDiscoveryBuilder:
    """Assemble, deduplicate, and score protocol discovery outputs."""

    def build(
        self,
        *,
        root_address: str,
        chain_id: int,
        protocol_name: str,
        protocol_family: str,
        contracts: list[ProtocolContract],
        relationships: list[ProtocolRelationship],
    ) -> ProtocolDiscoveryResult:
        deduped_contracts = _dedupe_contracts(contracts)
        deduped_relationships = _dedupe_relationships(relationships, deduped_contracts)
        ordered_contracts = _sort_contracts(deduped_contracts)
        ordered_relationships = _sort_relationships(deduped_relationships)
        detection_sources = _collect_detection_sources(ordered_contracts, ordered_relationships)
        confidence = _aggregate_confidence(ordered_contracts)

        return ProtocolDiscoveryResult(
            root_address=root_address,
            chain_id=chain_id,
            protocol_name=protocol_name or "unknown",
            protocol_family=protocol_family or "unknown",
            contracts=tuple(ordered_contracts),
            relationships=tuple(ordered_relationships),
            confidence=confidence,
            detection_sources=tuple(detection_sources),
        )


def _dedupe_contracts(contracts: list[ProtocolContract]) -> list[ProtocolContract]:
    best: dict[str, ProtocolContract] = {}
    for contract in contracts:
        existing = best.get(contract.address)
        if existing is None or contract.confidence > existing.confidence:
            best[contract.address] = contract
    return list(best.values())


def _dedupe_relationships(
    relationships: list[ProtocolRelationship],
    contracts: list[ProtocolContract],
) -> list[ProtocolRelationship]:
    known_addresses = {contract.address for contract in contracts}
    seen: set[tuple[str, str, str]] = set()
    unique: list[ProtocolRelationship] = []
    for relationship in relationships:
        if relationship.source_address not in known_addresses:
            continue
        if relationship.target_address not in known_addresses:
            continue
        key = (
            relationship.source_address,
            relationship.target_address,
            relationship.relationship_type.value,
        )
        if key in seen:
            continue
        seen.add(key)
        unique.append(relationship)
    return unique


def _sort_contracts(contracts: list[ProtocolContract]) -> list[ProtocolContract]:
    role_rank = {role: index for index, role in enumerate(ProtocolRole)}
    return sorted(
        contracts,
        key=lambda item: (role_rank.get(item.role, len(role_rank)), item.address),
    )


def _sort_relationships(relationships: list[ProtocolRelationship]) -> list[ProtocolRelationship]:
    return sorted(
        relationships,
        key=lambda item: (
            item.relationship_type.value,
            item.source_address,
            item.target_address,
        ),
    )


def _collect_detection_sources(
    contracts: list[ProtocolContract],
    relationships: list[ProtocolRelationship],
) -> list[str]:
    sources = {contract.detection_source for contract in contracts}
    sources.update(relationship.detection_source for relationship in relationships)
    return sorted(sources)


def _aggregate_confidence(contracts: list[ProtocolContract]) -> int:
    if not contracts:
        return 0
    rootish = [
        contract.confidence
        for contract in contracts
        if contract.role == ProtocolRole.ROOT or contract.metadata.get("is_root")
    ]
    if rootish:
        return min(rootish)
    return min(contract.confidence for contract in contracts)
