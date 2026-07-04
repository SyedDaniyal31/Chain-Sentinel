"""Protocol relationship analyzer integration tests (M6.3)."""

from app.blockchain.protocol.relationship_intelligence import enrich_protocol_intelligence
from app.blockchain.protocol.relationship_models import RelationshipAnalysisContext
from app.schemas.scan_result import (
    BridgeIntegrationData,
    DexIntegrationData,
    OracleIntegrationData,
    ProtocolIntelligenceData,
)
from app.services.protocol_relationship_analyzer import ProtocolRelationshipAnalyzer


def test_enrich_protocol_intelligence_adds_graph_and_relationships() -> None:
    protocol = ProtocolIntelligenceData(
        protocol_family="bridge",
        protocol_name="layerzero_endpoint",
        family="bridge",
        name="layerzero_endpoint",
        dexes=[DexIntegrationData(name="Uniswap V3", role="pool", confidence=90)],
        oracles=[OracleIntegrationData(name="Chainlink", confidence=88)],
        bridges=[BridgeIntegrationData(name="LayerZero", role="endpoint", confidence=94)],
    )
    context = RelationshipAnalysisContext(
        target_address="0x742d35cc6634c0532925a3b844bc9e7595f0beb0",
        protocol_family=protocol.protocol_family,
        protocol_name=protocol.protocol_name,
        dexes=[item.model_dump() for item in protocol.dexes],
        oracles=[item.model_dump() for item in protocol.oracles],
        bridges=[item.model_dump() for item in protocol.bridges],
        liquidity_has_liquidity=True,
        liquidity_primary_dex="uniswap",
        wallet_deployer="0xabcdefabcdefabcdefabcdefabcdefabcdefabcd",
        is_upgradeable=True,
        admin_address="0x1234567890123456789012345678901234567890",
    )

    enriched = enrich_protocol_intelligence(protocol, context)
    assert enriched.relationships
    assert enriched.architecture_graph.nodes
    assert enriched.architecture_graph.edges
    assert enriched.architecture_summary.application_type == "bridge"
    assert enriched.architecture_summary.bridge == "LayerZero"
    assert enriched.architecture_summary.oracle == "Chainlink"


def test_protocol_relationship_analyzer_preserves_legacy_protocol_fields() -> None:
    protocol = ProtocolIntelligenceData(
        protocol_family="token",
        protocol_name="erc20_token",
        standards=["ERC20"],
    )
    analyzer = ProtocolRelationshipAnalyzer()
    result = analyzer.analyze(
        "0x742d35cc6634c0532925a3b844bc9e7595f0beb0",
        protocol_intelligence=protocol,
        wallet_deployer="0xabcdefabcdefabcdefabcdefabcdefabcdefabcd",
    )
    assert result.protocol_family == "token"
    assert result.standards == ["ERC20"]
    assert isinstance(result.relationships, list)
    assert result.architecture_graph.nodes


def test_legacy_protocol_intelligence_without_m63_fields() -> None:
    payload = ProtocolIntelligenceData.model_validate(
        {
            "protocol_family": "dex",
            "protocol_name": "uniswap_v3_pool",
            "confidence": {"score": 80, "level": "high"},
        }
    )
    assert payload.relationships == []
    assert payload.architecture_graph.nodes == []
    assert payload.architecture_summary.application_type == "unknown"
