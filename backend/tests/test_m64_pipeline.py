"""M6.4 pipeline and legacy compatibility tests."""

from app.blockchain.security.threat_surface_analyzer import enrich_protocol_with_threat_surface
from app.blockchain.security.threat_models import ThreatSurfaceContext
from app.schemas.scan_result import (
    BridgeIntegrationData,
    OracleIntegrationData,
    ProtocolIntelligenceData,
    ProtocolRelationshipData,
    VaultIntegrationData,
)
from app.services.threat_surface_analyzer import ThreatSurfaceAnalyzer


def test_enrich_protocol_with_threat_surface_preserves_m63_fields() -> None:
    protocol = ProtocolIntelligenceData(
        protocol_family="bridge",
        protocol_name="layerzero_endpoint",
        bridges=[BridgeIntegrationData(name="LayerZero", role="endpoint", confidence=94)],
        oracles=[OracleIntegrationData(name="Chainlink", confidence=88)],
        relationships=[
            ProtocolRelationshipData(
                source="Target Contract",
                target="LayerZero (endpoint)",
                relationship_type="BRIDGES_WITH",
                confidence=94,
                detection_source="protocol_intelligence.bridge",
            )
        ],
    )
    context = ThreatSurfaceContext(
        target_address="0x742d35cc6634c0532925a3b844bc9e7595f0beb0",
        protocol_family=protocol.protocol_family,
        bridges=[item.model_dump() for item in protocol.bridges],
        oracles=[item.model_dump() for item in protocol.oracles],
        relationships=[item.model_dump() for item in protocol.relationships],
        is_upgradeable=True,
        admin_address="0x1234567890123456789012345678901234567890",
        wallet_owner="0xabcdefabcdefabcdefabcdefabcdefabcdefabcd",
    )
    enriched = enrich_protocol_with_threat_surface(protocol, context)
    assert enriched.protocol_family == "bridge"
    assert enriched.relationships
    assert enriched.threat_surface.external_dependencies
    assert enriched.threat_surface.attack_paths
    assert enriched.threat_surface.dependency_graph.nodes


def test_threat_surface_analyzer_service_enriches_protocol() -> None:
    protocol = ProtocolIntelligenceData(
        protocol_family="vault",
        vaults=[VaultIntegrationData(name="Yearn", type="ERC4626 Vault", confidence=90)],
    )
    analyzer = ThreatSurfaceAnalyzer()
    result = analyzer.analyze(
        "0x742d35cc6634c0532925a3b844bc9e7595f0beb0",
        protocol_intelligence=protocol,
        is_upgradeable=False,
    )
    assert result.threat_surface.trust_boundaries or result.threat_surface.external_dependencies


def test_legacy_protocol_intelligence_without_m64_threat_surface() -> None:
    payload = ProtocolIntelligenceData.model_validate(
        {
            "protocol_family": "token",
            "protocol_name": "erc20_token",
            "confidence": {"score": 55, "level": "medium"},
        }
    )
    assert payload.threat_surface.external_dependencies == []
    assert payload.threat_surface.dependency_graph.nodes == []
    assert payload.threat_surface.attack_paths == []
