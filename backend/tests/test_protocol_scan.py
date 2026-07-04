"""Unit tests for protocol discovery engine (M8.1)."""

from __future__ import annotations

from dataclasses import replace
from unittest.mock import AsyncMock, MagicMock

import pytest
from web3 import AsyncWeb3

from app.blockchain.contract_source_provider import VerifiedContractSource
from app.blockchain.protocol.defi_registry import DEFI_DEPLOYMENTS
from app.blockchain.protocol_scan.builder import ProtocolDiscoveryBuilder
from app.blockchain.protocol_scan.contract_classifier import ProtocolContractClassifier
from app.blockchain.protocol_scan.discovery import ProtocolDiscoveryEngine
from app.blockchain.protocol_scan.models import (
    ProtocolContract,
    ProtocolRelationshipType,
    ProtocolRole,
)
from app.blockchain.protocol_scan.provider import ContractProbeResult, ProtocolDiscoveryProvider
from app.blockchain.protocol_scan.registry import DiscoveryProviderRegistry, DuplicateDiscoveryProviderError
from app.blockchain.protocol_scan.relationship_detector import RelationshipDetector
from app.models.enums import ConfidenceLevel, GovernanceType
from app.schemas.scan_result import GovernanceAnalysisData, ProtocolIntelligenceData, ProtocolConfidenceData

UNISWAP_V2_FACTORY = "0x5c69bee701ef814a2b6a3edd4b1652cb9cc5aa6f"
UNISWAP_V2_ROUTER = "0x7a250d5630b4cf539739df2c5dacb4c659f2488d"
PROXY = "0xa231aa3388416ebc1b8f8a51b412327832524ca4"
IMPLEMENTATION = "0xdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef"
ADMIN = "0x1234567890123456789012345678901234567890"
YEARN_VAULT = "0x5f18c75abdae578b483e0628919e8f13bd7f7d0a"
CCTP_MESSENGER = "0x0a991d191182e2b023275e980142aaaf265c455e"
WORMHOLE_CORE = "0x98f3c9e6e3f36eaa832f396b124298900b640994"


class StaticDiscoveryProvider(ProtocolDiscoveryProvider):
    """Test provider backed by preconfigured probe results."""

    def __init__(self, probes: dict[str, ContractProbeResult]) -> None:
        self._probes = probes

    async def probe_contract(self, address: str, chain_id: int) -> ContractProbeResult:
        normalized = address.lower()
        if normalized not in self._probes:
            return ContractProbeResult(
                address=normalized,
                chain_id=chain_id,
                bytecode=b"\x60\x80",
            )
        probe = self._probes[normalized]
        if probe.chain_id != chain_id:
            return replace(probe, chain_id=chain_id)
        return probe


def _probe(
    address: str,
    *,
    chain_id: int = 1,
    bytecode: bytes = b"\x60\x80",
    implementation_address: str | None = None,
    admin_address: str | None = None,
    is_timelock: bool = False,
    verified_source: VerifiedContractSource | None = None,
    linked_addresses: tuple[str, ...] = (),
) -> ContractProbeResult:
    return ContractProbeResult(
        address=address.lower(),
        chain_id=chain_id,
        bytecode=bytecode,
        verified_source=verified_source,
        implementation_address=implementation_address.lower() if implementation_address else None,
        admin_address=admin_address.lower() if admin_address else None,
        is_timelock=is_timelock,
        linked_addresses=linked_addresses,
    )


def _engine_with_provider(probes: dict[str, ContractProbeResult], **kwargs) -> ProtocolDiscoveryEngine:
    web3 = MagicMock()
    provider = StaticDiscoveryProvider(probes)
    protocol_analyzer = MagicMock()
    protocol_analyzer.analyze = AsyncMock(return_value=ProtocolIntelligenceData())
    return ProtocolDiscoveryEngine(
        web3,
        provider=provider,
        protocol_intelligence_analyzer=protocol_analyzer,
        **kwargs,
    )


@pytest.mark.asyncio
async def test_proxy_discovery_adds_implementation_and_relationship() -> None:
    probes = {
        PROXY.lower(): _probe(
            PROXY,
            implementation_address=IMPLEMENTATION,
        ),
        IMPLEMENTATION.lower(): _probe(IMPLEMENTATION),
    }
    engine = _engine_with_provider(probes)
    result = await engine.discover(PROXY, chain_id=1)

    roles = {contract.address: contract.role for contract in result.contracts}
    assert roles[PROXY.lower()] in {ProtocolRole.ROOT, ProtocolRole.PROXY}
    assert IMPLEMENTATION.lower() in roles
    assert roles[IMPLEMENTATION.lower()] == ProtocolRole.IMPLEMENTATION
    assert any(
        rel.relationship_type == ProtocolRelationshipType.PROXY_TO_IMPLEMENTATION
        for rel in result.relationships
    )


@pytest.mark.asyncio
async def test_governance_discovery_adds_timelock_authority() -> None:
    probes = {
        PROXY.lower(): _probe(PROXY, admin_address=ADMIN),
        ADMIN.lower(): _probe(ADMIN, is_timelock=True),
    }
    governance = GovernanceAnalysisData(
        governance_type=GovernanceType.TIMELOCK,
        has_timelock=True,
        source_confidence=ConfidenceLevel.HIGH,
    )
    governance_analyzer = MagicMock()
    governance_analyzer.analyze = AsyncMock(return_value=governance)
    engine = _engine_with_provider(probes, governance_analyzer=governance_analyzer)

    result = await engine.discover(PROXY, chain_id=1)
    assert any(contract.role == ProtocolRole.TIMELOCK for contract in result.contracts)
    assert any(
        rel.relationship_type == ProtocolRelationshipType.GOVERNOR_TO_TIMELOCK
        for rel in result.relationships
    ) or any(contract.address == ADMIN.lower() for contract in result.contracts)


@pytest.mark.asyncio
async def test_dex_discovery_links_router_to_factory() -> None:
    probes = {
        UNISWAP_V2_FACTORY: _probe(UNISWAP_V2_FACTORY),
        UNISWAP_V2_ROUTER: _probe(UNISWAP_V2_ROUTER),
    }
    engine = _engine_with_provider(probes)
    result = await engine.discover(UNISWAP_V2_FACTORY, chain_id=1)

    assert result.protocol_name == "Uniswap V2"
    assert result.protocol_family == "dex"
    assert any(contract.role == ProtocolRole.FACTORY for contract in result.contracts)
    assert any(contract.role == ProtocolRole.ROUTER for contract in result.contracts)
    assert any(
        rel.relationship_type == ProtocolRelationshipType.ROUTER_TO_FACTORY
        and rel.source_address == UNISWAP_V2_ROUTER
        and rel.target_address == UNISWAP_V2_FACTORY
        for rel in result.relationships
    )


@pytest.mark.asyncio
async def test_vault_discovery_from_registry() -> None:
    probes = {YEARN_VAULT: _probe(YEARN_VAULT)}
    engine = _engine_with_provider(probes)
    result = await engine.discover(YEARN_VAULT, chain_id=1)

    assert result.protocol_name == "Yearn"
    assert any(contract.role == ProtocolRole.VAULT for contract in result.contracts)


@pytest.mark.asyncio
async def test_builder_deduplicates_contracts_by_address() -> None:
    builder = ProtocolDiscoveryBuilder()
    result = builder.build(
        root_address=PROXY.lower(),
        chain_id=1,
        protocol_name="Sample",
        protocol_family="dex",
        contracts=[
            ProtocolContract(PROXY.lower(), ProtocolRole.ROOT, 80, "a"),
            ProtocolContract(PROXY.lower(), ProtocolRole.PROXY, 95, "b"),
        ],
        relationships=[],
    )
    assert len(result.contracts) == 1
    assert result.contracts[0].confidence == 95


@pytest.mark.asyncio
async def test_unknown_protocol_fallback() -> None:
    probes = {"0x1111111111111111111111111111111111111111": _probe("0x1111111111111111111111111111111111111111")}
    engine = _engine_with_provider(probes)
    result = await engine.discover("0x1111111111111111111111111111111111111111", chain_id=1)

    assert result.protocol_name == "unknown"
    assert result.protocol_family == "unknown"
    assert result.confidence == 95


def test_confidence_propagation_uses_root_contract_score() -> None:
    builder = ProtocolDiscoveryBuilder()
    result = builder.build(
        root_address=PROXY.lower(),
        chain_id=1,
        protocol_name="Sample",
        protocol_family="dex",
        contracts=[
            ProtocolContract(PROXY.lower(), ProtocolRole.ROOT, 88, "root"),
            ProtocolContract(IMPLEMENTATION.lower(), ProtocolRole.IMPLEMENTATION, 95, "impl"),
        ],
        relationships=[],
    )
    assert result.confidence == 88


@pytest.mark.asyncio
async def test_deterministic_output_ordering() -> None:
    probes = {
        UNISWAP_V2_FACTORY: _probe(UNISWAP_V2_FACTORY),
        UNISWAP_V2_ROUTER: _probe(UNISWAP_V2_ROUTER),
    }
    engine = _engine_with_provider(probes)
    first = await engine.discover(UNISWAP_V2_FACTORY, chain_id=1)
    second = await engine.discover(UNISWAP_V2_FACTORY, chain_id=1)
    assert first == second


def test_registry_rejects_duplicate_provider_names() -> None:
    registry = DiscoveryProviderRegistry()
    provider = StaticDiscoveryProvider({})
    registry.register("custom", provider)
    with pytest.raises(DuplicateDiscoveryProviderError):
        registry.register("custom", provider)


def test_relationship_detector_bridge_to_messenger() -> None:
    detector = RelationshipDetector()
    contracts = [
        ProtocolContract(
            WORMHOLE_CORE,
            ProtocolRole.BRIDGE,
            90,
            "registry",
            metadata={"protocol": "Wormhole"},
        ),
        ProtocolContract(
            "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            ProtocolRole.MESSENGER,
            85,
            "registry",
            metadata={"protocol": "Wormhole"},
        ),
    ]
    relationships = detector.detect(contracts)
    assert any(
        rel.relationship_type == ProtocolRelationshipType.BRIDGE_TO_MESSENGER
        for rel in relationships
    )


def test_classifier_confidence_from_governance() -> None:
    classifier = ProtocolContractClassifier()
    contract = classifier.classify_governance_authority(
        ADMIN,
        GovernanceAnalysisData(source_confidence=ConfidenceLevel.LOW),
        is_timelock=False,
    )
    assert contract.confidence == 45


def test_defi_registry_contains_uniswap_factory() -> None:
    assert any(
        deployment.address.lower() == UNISWAP_V2_FACTORY and deployment.role == "factory"
        for deployment in DEFI_DEPLOYMENTS
    )
