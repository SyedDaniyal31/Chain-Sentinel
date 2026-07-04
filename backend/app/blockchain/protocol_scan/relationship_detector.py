"""Protocol relationship detection (M8.1)."""

from __future__ import annotations

from app.blockchain.protocol.defi_registry import DEFI_DEPLOYMENTS
from app.blockchain.protocol_scan.models import (
    ProtocolContract,
    ProtocolRelationship,
    ProtocolRelationshipType,
    ProtocolRole,
)


class RelationshipDetector:
    """Create typed protocol edges from discovered contract roles."""

    def detect(self, contracts: list[ProtocolContract]) -> list[ProtocolRelationship]:
        by_address = {contract.address: contract for contract in contracts}
        by_role: dict[ProtocolRole, list[ProtocolContract]] = {}
        for contract in contracts:
            by_role.setdefault(contract.role, []).append(contract)

        relationships: list[ProtocolRelationship] = []
        relationships.extend(self._proxy_relationships(by_role))
        relationships.extend(self._governance_relationships(by_role))
        relationships.extend(self._dex_relationships(contracts, by_role))
        relationships.extend(self._vault_relationships(by_role))
        relationships.extend(self._treasury_relationships(by_role))
        relationships.extend(self._bridge_relationships(by_role))
        relationships.extend(self._factory_pool_relationships(by_address, contracts))
        return _dedupe_relationships(relationships)

    @staticmethod
    def _proxy_relationships(by_role: dict[ProtocolRole, list[ProtocolContract]]) -> list[ProtocolRelationship]:
        relationships: list[ProtocolRelationship] = []
        proxies = by_role.get(ProtocolRole.PROXY, [])
        implementations = by_role.get(ProtocolRole.IMPLEMENTATION, [])
        for proxy in proxies:
            impl_address = proxy.metadata.get("implementation_address")
            targets = [
                item
                for item in implementations
                if impl_address is None or item.address == impl_address
            ] or implementations
            for implementation in targets:
                relationships.append(
                    ProtocolRelationship(
                        source_address=proxy.address,
                        target_address=implementation.address,
                        relationship_type=ProtocolRelationshipType.PROXY_TO_IMPLEMENTATION,
                        confidence=min(proxy.confidence, implementation.confidence),
                        detection_source="relationship_detector.proxy",
                    )
                )
        return relationships

    @staticmethod
    def _governance_relationships(
        by_role: dict[ProtocolRole, list[ProtocolContract]],
    ) -> list[ProtocolRelationship]:
        relationships: list[ProtocolRelationship] = []
        governors = by_role.get(ProtocolRole.GOVERNOR, [])
        timelocks = by_role.get(ProtocolRole.TIMELOCK, [])
        for governor in governors:
            for timelock in timelocks:
                relationships.append(
                    ProtocolRelationship(
                        source_address=governor.address,
                        target_address=timelock.address,
                        relationship_type=ProtocolRelationshipType.GOVERNOR_TO_TIMELOCK,
                        confidence=min(governor.confidence, timelock.confidence),
                        detection_source="relationship_detector.governance",
                    )
                )
        return relationships

    @staticmethod
    def _dex_relationships(
        contracts: list[ProtocolContract],
        by_role: dict[ProtocolRole, list[ProtocolContract]],
    ) -> list[ProtocolRelationship]:
        relationships: list[ProtocolRelationship] = []
        routers = by_role.get(ProtocolRole.ROUTER, [])
        factories = by_role.get(ProtocolRole.FACTORY, [])
        if routers and factories:
            for router in routers:
                for factory in factories:
                    if _same_protocol(router, factory):
                        relationships.append(
                            ProtocolRelationship(
                                source_address=router.address,
                                target_address=factory.address,
                                relationship_type=ProtocolRelationshipType.ROUTER_TO_FACTORY,
                                confidence=min(router.confidence, factory.confidence),
                                detection_source="relationship_detector.dex",
                            )
                        )
            return relationships

        for contract in contracts:
            if contract.role != ProtocolRole.FACTORY:
                continue
            protocol = contract.metadata.get("protocol")
            chain_id = contract.metadata.get("chain_id")
            if not protocol or chain_id is None:
                continue
            router = _find_paired_deployment(protocol, "router", int(chain_id))
            if router is None:
                continue
            relationships.append(
                ProtocolRelationship(
                    source_address=router,
                    target_address=contract.address,
                    relationship_type=ProtocolRelationshipType.ROUTER_TO_FACTORY,
                    confidence=contract.confidence,
                    detection_source="relationship_detector.registry_pair",
                )
            )
        return relationships

    @staticmethod
    def _vault_relationships(
        by_role: dict[ProtocolRole, list[ProtocolContract]],
    ) -> list[ProtocolRelationship]:
        relationships: list[ProtocolRelationship] = []
        vaults = by_role.get(ProtocolRole.VAULT, [])
        strategies = by_role.get(ProtocolRole.STRATEGY, [])
        for vault in vaults:
            for strategy in strategies:
                relationships.append(
                    ProtocolRelationship(
                        source_address=vault.address,
                        target_address=strategy.address,
                        relationship_type=ProtocolRelationshipType.VAULT_TO_STRATEGY,
                        confidence=min(vault.confidence, strategy.confidence),
                        detection_source="relationship_detector.vault",
                    )
                )
        return relationships

    @staticmethod
    def _treasury_relationships(
        by_role: dict[ProtocolRole, list[ProtocolContract]],
    ) -> list[ProtocolRelationship]:
        relationships: list[ProtocolRelationship] = []
        tokens = by_role.get(ProtocolRole.TOKEN, []) + by_role.get(ProtocolRole.ROOT, [])
        treasuries = by_role.get(ProtocolRole.TREASURY, [])
        for token in tokens:
            for treasury in treasuries:
                relationships.append(
                    ProtocolRelationship(
                        source_address=token.address,
                        target_address=treasury.address,
                        relationship_type=ProtocolRelationshipType.TOKEN_TO_TREASURY,
                        confidence=min(token.confidence, treasury.confidence),
                        detection_source="relationship_detector.treasury",
                    )
                )
        return relationships

    @staticmethod
    def _bridge_relationships(
        by_role: dict[ProtocolRole, list[ProtocolContract]],
    ) -> list[ProtocolRelationship]:
        relationships: list[ProtocolRelationship] = []
        bridges = by_role.get(ProtocolRole.BRIDGE, [])
        messengers = by_role.get(ProtocolRole.MESSENGER, [])
        for bridge in bridges:
            for messenger in messengers:
                if not _same_protocol(bridge, messenger):
                    continue
                relationships.append(
                    ProtocolRelationship(
                        source_address=bridge.address,
                        target_address=messenger.address,
                        relationship_type=ProtocolRelationshipType.BRIDGE_TO_MESSENGER,
                        confidence=min(bridge.confidence, messenger.confidence),
                        detection_source="relationship_detector.bridge",
                    )
                )
        return relationships

    @staticmethod
    def _factory_pool_relationships(
        by_address: dict[str, ProtocolContract],
        contracts: list[ProtocolContract],
    ) -> list[ProtocolRelationship]:
        relationships: list[ProtocolRelationship] = []
        for contract in contracts:
            if contract.role != ProtocolRole.POOL:
                continue
            factory_address = contract.metadata.get("factory_address")
            if factory_address and factory_address in by_address:
                relationships.append(
                    ProtocolRelationship(
                        source_address=factory_address,
                        target_address=contract.address,
                        relationship_type=ProtocolRelationshipType.FACTORY_TO_POOL,
                        confidence=contract.confidence,
                        detection_source="relationship_detector.pool",
                    )
                )
        return relationships


def _same_protocol(left: ProtocolContract, right: ProtocolContract) -> bool:
    left_protocol = left.metadata.get("protocol")
    right_protocol = right.metadata.get("protocol")
    if left_protocol and right_protocol:
        return left_protocol == right_protocol
    return False


def _find_paired_deployment(protocol: str, role: str, chain_id: int) -> str | None:
    for deployment in DEFI_DEPLOYMENTS:
        if deployment.protocol == protocol and deployment.role == role and deployment.chain_id == chain_id:
            return deployment.address.lower()
    return None


def _dedupe_relationships(
    relationships: list[ProtocolRelationship],
) -> list[ProtocolRelationship]:
    seen: set[tuple[str, str, str]] = set()
    unique: list[ProtocolRelationship] = []
    for relationship in relationships:
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
