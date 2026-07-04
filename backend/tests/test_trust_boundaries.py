"""Trust boundary detector unit tests (M6.4)."""

import app.blockchain.security.threat_models as threat_models
from app.blockchain.security.trust_boundary_detector import detect_trust_boundaries

TrustBoundaryKind = threat_models.TrustBoundaryKind
ThreatSurfaceContext = threat_models.ThreatSurfaceContext


def test_detect_trust_boundaries_from_protocol_integrations() -> None:
    context = ThreatSurfaceContext(
        target_address="0x742d35cc6634c0532925a3b844bc9e7595f0beb0",
        oracles=[{"name": "Chainlink", "confidence": 88}],
        bridges=[{"name": "LayerZero", "role": "endpoint", "confidence": 94}],
        vaults=[{"name": "Yearn", "type": "ERC4626 Vault", "confidence": 90}],
    )
    boundaries = detect_trust_boundaries(context)
    types = {item.boundary_type for item in boundaries}
    assert TrustBoundaryKind.ORACLE in types
    assert TrustBoundaryKind.BRIDGE in types
    assert TrustBoundaryKind.VAULT in types


def test_detect_trust_boundaries_from_governance_and_proxy() -> None:
    context = ThreatSurfaceContext(
        target_address="0x742d35cc6634c0532925a3b844bc9e7595f0beb0",
        has_timelock=True,
        is_upgradeable=True,
        proxy_type="transparent",
        wallet_owner="0xabcdefabcdefabcdefabcdefabcdefabcdefabcd",
        treasury_is_multisig=True,
        wallet_treasury="0xcccccccccccccccccccccccccccccccccccccccc",
    )
    boundaries = detect_trust_boundaries(context)
    types = {item.boundary_type for item in boundaries}
    assert TrustBoundaryKind.TIMELOCK in types
    assert TrustBoundaryKind.OWNER in types
    assert TrustBoundaryKind.UPGRADEABLE_PROXY in types
    assert TrustBoundaryKind.MULTISIG in types
