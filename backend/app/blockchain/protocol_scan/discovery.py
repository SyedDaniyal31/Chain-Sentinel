"""Protocol discovery engine orchestration (M8.1)."""

from __future__ import annotations

import logging

from web3 import AsyncWeb3

from app.blockchain.contract_source_provider import ContractSourceProvider, NullContractSourceProvider
from app.blockchain.protocol.bridge_registry import BRIDGE_DEPLOYMENTS
from app.blockchain.protocol.defi_registry import DEFI_DEPLOYMENTS
from app.blockchain.protocol_scan.builder import ProtocolDiscoveryBuilder
from app.blockchain.protocol_scan.contract_classifier import ProtocolContractClassifier
from app.blockchain.protocol_scan.models import ProtocolContract, ProtocolDiscoveryResult, ProtocolRole
from app.blockchain.protocol_scan.provider import (
    ContractProbeResult,
    OnChainProtocolDiscoveryProvider,
    ProtocolDiscoveryProvider,
)
from app.blockchain.protocol_scan.registry import DiscoveryProviderRegistry
from app.blockchain.protocol_scan.relationship_detector import RelationshipDetector
from app.core.validators import normalize_eth_address
from app.models.enums import AdminType, ContractType
from app.services.governance_analyzer import GovernanceAnalyzer
from app.services.liquidity_analyzer import LiquidityAnalyzer
from app.services.protocol_intelligence_analyzer import ProtocolIntelligenceAnalyzer
from app.services.wallet_intelligence_analyzer import WalletIntelligenceAnalyzer

logger = logging.getLogger(__name__)


class ProtocolDiscoveryEngine:
    """
    Discover all contracts belonging to the same protocol starting from a root address.

    The engine delegates on-chain probing to pluggable providers and reuses existing
    ChainSentinel analyzers without modifying their behavior.
    """

    def __init__(
        self,
        web3: AsyncWeb3,
        *,
        provider: ProtocolDiscoveryProvider | None = None,
        provider_registry: DiscoveryProviderRegistry | None = None,
        source_provider: ContractSourceProvider | None = None,
        governance_analyzer: GovernanceAnalyzer | None = None,
        liquidity_analyzer: LiquidityAnalyzer | None = None,
        wallet_analyzer: WalletIntelligenceAnalyzer | None = None,
        protocol_intelligence_analyzer: ProtocolIntelligenceAnalyzer | None = None,
        classifier: ProtocolContractClassifier | None = None,
        relationship_detector: RelationshipDetector | None = None,
        builder: ProtocolDiscoveryBuilder | None = None,
    ) -> None:
        self._web3 = web3
        self._source_provider = source_provider or NullContractSourceProvider()
        self._governance_analyzer = governance_analyzer
        self._liquidity_analyzer = liquidity_analyzer
        self._wallet_analyzer = wallet_analyzer
        self._protocol_intelligence_analyzer = (
            protocol_intelligence_analyzer or ProtocolIntelligenceAnalyzer(web3)
        )
        self._classifier = classifier or ProtocolContractClassifier()
        self._relationship_detector = relationship_detector or RelationshipDetector()
        self._builder = builder or ProtocolDiscoveryBuilder()

        self._provider_registry = provider_registry or DiscoveryProviderRegistry()
        if provider is not None:
            self._provider = provider
        else:
            on_chain = OnChainProtocolDiscoveryProvider(
                web3,
                source_provider=self._source_provider,
            )
            if DiscoveryProviderRegistry.DEFAULT_PROVIDER not in self._provider_registry.all_names():
                self._provider_registry.register(
                    DiscoveryProviderRegistry.DEFAULT_PROVIDER,
                    on_chain,
                )
            self._provider = on_chain

    @property
    def provider_registry(self) -> DiscoveryProviderRegistry:
        return self._provider_registry

    async def discover(
        self,
        root_address: str,
        chain_id: int = 1,
        *,
        provider_name: str = DiscoveryProviderRegistry.DEFAULT_PROVIDER,
    ) -> ProtocolDiscoveryResult:
        """Discover related contracts, classify roles, and assemble a protocol graph."""
        normalized_root = normalize_eth_address(root_address)
        provider = self._provider if provider_name == DiscoveryProviderRegistry.DEFAULT_PROVIDER else self._provider_registry.require(provider_name)

        probes: dict[str, ContractProbeResult] = {}
        contracts: list[ProtocolContract] = []
        relationships = []

        root_probe = await provider.probe_contract(normalized_root, chain_id)
        probes[normalized_root] = root_probe

        registry_contract = self._classifier.classify_from_registry(normalized_root, chain_id)
        if registry_contract is not None:
            contracts.append(
                ProtocolContract(
                    address=registry_contract.address,
                    role=registry_contract.role,
                    confidence=max(registry_contract.confidence, 95),
                    detection_source=registry_contract.detection_source,
                    metadata={**registry_contract.metadata, "is_root": True},
                )
            )
        else:
            contracts.append(self._classifier.classify_root(root_probe))

        contracts.extend(await self._discover_proxy_chain(root_probe, probes, provider, chain_id))
        contracts.extend(await self._discover_governance_chain(root_probe, probes, provider, chain_id))
        contracts.extend(await self._discover_registry_peers(normalized_root, chain_id))
        contracts.extend(await self._discover_from_intelligence(root_probe, chain_id))
        contracts.extend(await self._discover_wallet_treasury(root_probe))
        contracts.extend(await self._discover_liquidity_pools(normalized_root))
        contracts.extend(self._discover_source_linked_contracts(root_probe, probes, chain_id))

        relationships = self._relationship_detector.detect(contracts)
        protocol_name, protocol_family = _resolve_protocol_identity(contracts)

        return self._builder.build(
            root_address=normalized_root,
            chain_id=chain_id,
            protocol_name=protocol_name,
            protocol_family=protocol_family,
            contracts=contracts,
            relationships=relationships,
        )

    async def _discover_proxy_chain(
        self,
        root_probe: ContractProbeResult,
        probes: dict[str, ContractProbeResult],
        provider: ProtocolDiscoveryProvider,
        chain_id: int,
    ) -> list[ProtocolContract]:
        if not root_probe.implementation_address:
            return []

        implementation_address = normalize_eth_address(root_probe.implementation_address)
        proxy, implementation = self._classifier.classify_proxy_implementation(
            root_probe.address,
            implementation_address,
        )
        proxy = ProtocolContract(
            address=proxy.address,
            role=proxy.role,
            confidence=proxy.confidence,
            detection_source=proxy.detection_source,
            metadata={**proxy.metadata, "implementation_address": implementation_address},
        )
        discovered = [proxy, implementation]

        impl_probe = await provider.probe_contract(implementation_address, chain_id)
        probes[implementation_address] = impl_probe
        discovered.append(
            self._classifier.classify_probe(
                impl_probe,
                default_role=ProtocolRole.IMPLEMENTATION,
                detection_source="verified_source.implementation",
                confidence=85,
            )
        )
        return discovered

    async def _discover_governance_chain(
        self,
        root_probe: ContractProbeResult,
        probes: dict[str, ContractProbeResult],
        provider: ProtocolDiscoveryProvider,
        chain_id: int,
    ) -> list[ProtocolContract]:
        if not root_probe.admin_address:
            return []

        admin_address = normalize_eth_address(root_probe.admin_address)
        admin_probe = await provider.probe_contract(admin_address, chain_id)
        probes[admin_address] = admin_probe

        if self._governance_analyzer is not None:
            try:
                governance = await self._governance_analyzer.analyze(
                    root_probe.address,
                    bytecode=root_probe.bytecode,
                    logic_address=root_probe.implementation_address or root_probe.address,
                    logic_bytecode=admin_probe.bytecode or root_probe.bytecode,
                    is_upgradeable=root_probe.implementation_address is not None,
                    admin_address=admin_address,
                    admin_type=AdminType.CONTRACT,
                    owner_address=None,
                    owner_type=None,
                    is_timelock=admin_probe.is_timelock or root_probe.is_timelock,
                    ownership_capability=False,
                    contract_type=ContractType.UNKNOWN,
                )
                authority = self._classifier.classify_governance_authority(
                    admin_address,
                    governance,
                    is_timelock=admin_probe.is_timelock,
                )
                return [authority]
            except Exception:
                logger.debug("Governance analyzer failed during protocol discovery", exc_info=True)

        role = ProtocolRole.TIMELOCK if admin_probe.is_timelock else ProtocolRole.GOVERNOR
        return [
            ProtocolContract(
                address=admin_address,
                role=role,
                confidence=75,
                detection_source="proxy_resolution.admin",
                metadata={"is_timelock": admin_probe.is_timelock},
            )
        ]

    async def _discover_registry_peers(
        self,
        root_address: str,
        chain_id: int,
    ) -> list[ProtocolContract]:
        contracts: list[ProtocolContract] = []
        root_registry = self._classifier.classify_from_registry(root_address, chain_id)
        if root_registry is None:
            return contracts

        protocol = root_registry.metadata.get("protocol")
        role = root_registry.metadata.get("registry_role")
        if not protocol or not role:
            return contracts

        if role == "factory":
            router = _find_defi_peer(protocol, "router", chain_id)
            if router and router != root_address:
                peer = self._classifier.classify_from_registry(router, chain_id)
                if peer is not None:
                    contracts.append(peer)
        elif role in {"endpoint", "core", "gateway", "mailbox"}:
            messenger = _find_bridge_peer(protocol, "messenger", chain_id)
            if messenger and messenger != root_address:
                peer = self._classifier.classify_from_registry(messenger, chain_id)
                if peer is not None:
                    contracts.append(peer)
        return contracts

    async def _discover_from_intelligence(
        self,
        root_probe: ContractProbeResult,
        chain_id: int,
    ) -> list[ProtocolContract]:
        verified = root_probe.verified_source
        intelligence = await self._protocol_intelligence_analyzer.analyze(
            root_probe.address,
            bytecode=root_probe.bytecode,
            chain_id=chain_id,
            implementation_bytecode=root_probe.bytecode,
            implementation_address=root_probe.implementation_address,
            admin_address=root_probe.admin_address,
            is_timelock=root_probe.is_timelock,
            is_verified=bool(verified and verified.is_verified),
            verified_source_code=verified.source_code if verified else None,
            contract_name=verified.contract_name if verified else None,
        )
        contracts: list[ProtocolContract] = []
        classified = self._classifier.classify_from_intelligence(root_probe.address, intelligence)
        if classified is not None:
            contracts.append(classified)

        if intelligence.vaults:
            contracts.append(
                ProtocolContract(
                    address=root_probe.address,
                    role=ProtocolRole.STRATEGY,
                    confidence=min(item.confidence for item in intelligence.vaults),
                    detection_source="protocol_intelligence.vault",
                    metadata={"vault_protocol": intelligence.vaults[0].name},
                )
            )
        if intelligence.oracles:
            contracts.append(
                ProtocolContract(
                    address=root_probe.address,
                    role=ProtocolRole.ORACLE,
                    confidence=min(item.confidence for item in intelligence.oracles),
                    detection_source="protocol_intelligence.oracle",
                    metadata={"oracle_protocol": intelligence.oracles[0].name},
                )
            )
        return contracts

    async def _discover_wallet_treasury(self, root_probe: ContractProbeResult) -> list[ProtocolContract]:
        if self._wallet_analyzer is None:
            return []
        try:
            wallet = await self._wallet_analyzer.analyze(
                root_probe.address,
                admin_address=root_probe.admin_address,
                admin_type=AdminType.CONTRACT if root_probe.admin_address else None,
                owner_address=None,
                owner_type=None,
                governance_ownership_address=None,
                is_timelock=root_probe.is_timelock,
            )
        except Exception:
            logger.debug("Wallet analyzer failed during protocol discovery", exc_info=True)
            return []

        treasury = wallet.ownership.treasury
        if not treasury:
            return []
        return [self._classifier.classify_treasury(normalize_eth_address(treasury))]

    async def _discover_liquidity_pools(self, root_address: str) -> list[ProtocolContract]:
        if self._liquidity_analyzer is None:
            return []
        try:
            liquidity = await self._liquidity_analyzer.analyze(root_address)
        except Exception:
            logger.debug("Liquidity analyzer failed during protocol discovery", exc_info=True)
            return []

        contracts: list[ProtocolContract] = []
        for pool in liquidity.top_pools[:3]:
            contracts.append(
                ProtocolContract(
                    address=normalize_eth_address(pool.pair_address),
                    role=ProtocolRole.POOL,
                    confidence=70,
                    detection_source="liquidity_analyzer",
                    metadata={
                        "dex": pool.dex,
                        "factory_address": None,
                    },
                )
            )
        return contracts

    def _discover_source_linked_contracts(
        self,
        root_probe: ContractProbeResult,
        probes: dict[str, ContractProbeResult],
        chain_id: int,
    ) -> list[ProtocolContract]:
        contracts: list[ProtocolContract] = []
        for linked in root_probe.linked_addresses[:5]:
            if linked in probes:
                continue
            registry_contract = self._classifier.classify_from_registry(linked, chain_id)
            if registry_contract is not None:
                contracts.append(registry_contract)
        return contracts


def _resolve_protocol_identity(contracts: list[ProtocolContract]) -> tuple[str, str]:
    for contract in contracts:
        protocol = contract.metadata.get("protocol")
        if protocol:
            family = contract.metadata.get("protocol_family") or _family_from_role(contract.role)
            return str(protocol), str(family)
        protocol_name = contract.metadata.get("protocol_name")
        if protocol_name and protocol_name != "unknown":
            return str(protocol_name), str(contract.metadata.get("protocol_family", "unknown"))
    return "unknown", "unknown"


def _family_from_role(role: ProtocolRole) -> str:
    mapping = {
        ProtocolRole.FACTORY: "dex",
        ProtocolRole.ROUTER: "dex",
        ProtocolRole.POOL: "dex",
        ProtocolRole.VAULT: "vault",
        ProtocolRole.BRIDGE: "bridge",
        ProtocolRole.MESSENGER: "bridge",
        ProtocolRole.GOVERNOR: "governance",
        ProtocolRole.TIMELOCK: "governance",
        ProtocolRole.ORACLE: "oracle",
    }
    return mapping.get(role, "unknown")


def _find_defi_peer(protocol: str, role: str, chain_id: int) -> str | None:
    for deployment in DEFI_DEPLOYMENTS:
        if deployment.protocol == protocol and deployment.role == role and deployment.chain_id == chain_id:
            return deployment.address.lower()
    return None


def _find_bridge_peer(protocol: str, role: str, chain_id: int) -> str | None:
    for deployment in BRIDGE_DEPLOYMENTS:
        if deployment.protocol == protocol and deployment.role == role and deployment.chain_id == chain_id:
            return deployment.address.lower()
    return None
