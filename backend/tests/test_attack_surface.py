"""Attack surface builder unit tests (M6.4)."""

from app.blockchain.security.attack_surface_builder import build_critical_assets, build_threat_surface
from app.blockchain.security.threat_models import DependencyCategory, ExternalDependency, ThreatSurfaceContext


def test_build_threat_surface_aggregates_all_sections() -> None:
    context = ThreatSurfaceContext(
        target_address="0x742d35cc6634c0532925a3b844bc9e7595f0beb0",
        protocol_family="bridge",
        proxy_type="transparent",
        is_upgradeable=True,
        admin_address="0x1234567890123456789012345678901234567890",
        implementation_address="0xdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef",
        bridges=[{"name": "LayerZero", "role": "endpoint", "confidence": 94}],
        oracles=[{"name": "Chainlink", "confidence": 88}],
        vaults=[{"name": "Yearn", "type": "ERC4626 Vault", "confidence": 90}],
        dexes=[{"name": "Uniswap V3", "role": "pool", "confidence": 85}],
        governance_protocols=[{"name": "Governor Bravo", "confidence": 92}],
        wallet_owner="0xabcdefabcdefabcdefabcdefabcdefabcdefabcd",
        liquidity_has_liquidity=True,
        liquidity_primary_dex="uniswap",
    )
    result = build_threat_surface(context)
    assert result.external_dependencies
    assert result.trust_boundaries
    assert result.privileged_entities
    assert result.attack_paths
    assert result.dependency_graph.nodes
    assert result.critical_assets


def test_build_critical_assets_includes_contract_and_vault() -> None:
    context = ThreatSurfaceContext(
        target_address="0x742d35cc6634c0532925a3b844bc9e7595f0beb0",
        implementation_address="0xdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef",
    )
    dependencies = [
        ExternalDependency(
            category=DependencyCategory.VAULT,
            name="Yearn",
            role="ERC4626 Vault",
            confidence=90,
            detection_source="protocol_intelligence.vault",
        )
    ]
    assets = build_critical_assets(context, dependencies)
    assert any(asset.asset_type == "contract" for asset in assets)
    assert any(asset.asset_type == "implementation" for asset in assets)
    assert any(asset.asset_type == "vault" for asset in assets)
