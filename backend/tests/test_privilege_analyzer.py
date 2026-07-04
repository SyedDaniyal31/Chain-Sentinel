"""Privilege analyzer unit tests (M6.4)."""

from app.blockchain.security.privilege_analyzer import analyze_privileged_entities
from app.blockchain.security.threat_models import PrivilegedEntityType, ThreatSurfaceContext


def test_analyze_privileged_entities_detects_owner_and_proxy_admin() -> None:
    context = ThreatSurfaceContext(
        target_address="0x742d35cc6634c0532925a3b844bc9e7595f0beb0",
        is_upgradeable=True,
        admin_address="0x1234567890123456789012345678901234567890",
        wallet_owner="0xabcdefabcdefabcdefabcdefabcdefabcdefabcd",
    )
    entities = analyze_privileged_entities(context)
    types = {item.entity_type for item in entities}
    assert PrivilegedEntityType.OWNER in types
    assert PrivilegedEntityType.PROXY_ADMIN in types


def test_analyze_privileged_entities_detects_bridge_relayer_and_oracle_admin() -> None:
    context = ThreatSurfaceContext(
        target_address="0x742d35cc6634c0532925a3b844bc9e7595f0beb0",
        bridges=[{"name": "LayerZero", "role": "endpoint", "confidence": 94}],
        oracles=[{"name": "Chainlink", "confidence": 88}],
    )
    entities = analyze_privileged_entities(context)
    types = {item.entity_type for item in entities}
    assert PrivilegedEntityType.BRIDGE_RELAYER in types
    assert PrivilegedEntityType.ORACLE_ADMIN in types


def test_analyze_privileged_entities_detects_capability_controller() -> None:
    context = ThreatSurfaceContext(
        target_address="0x742d35cc6634c0532925a3b844bc9e7595f0beb0",
        capability_controllers=[("mint", "0x1111111111111111111111111111111111111111")],
    )
    entities = analyze_privileged_entities(context)
    assert any(item.entity_type == PrivilegedEntityType.CAPABILITY_CONTROLLER for item in entities)
