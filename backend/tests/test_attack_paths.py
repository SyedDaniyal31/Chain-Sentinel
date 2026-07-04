"""Attack path builder unit tests (M6.4)."""

from app.blockchain.security.attack_path_builder import build_attack_paths
from app.blockchain.security.dependency_analyzer import analyze_external_dependencies
from app.blockchain.security.privilege_analyzer import analyze_privileged_entities
from app.blockchain.security.threat_models import ThreatSurfaceContext
from app.blockchain.security.trust_boundary_detector import detect_trust_boundaries


def test_build_attack_paths_oracle_vault_chain() -> None:
    context = ThreatSurfaceContext(
        target_address="0x742d35cc6634c0532925a3b844bc9e7595f0beb0",
        oracles=[{"name": "Chainlink", "confidence": 88}],
        vaults=[{"name": "Yearn", "type": "ERC4626 Vault", "confidence": 90}],
    )
    dependencies = analyze_external_dependencies(context)
    boundaries = detect_trust_boundaries(context)
    privileged = analyze_privileged_entities(context)
    paths = build_attack_paths(context, dependencies, boundaries, privileged)
    assert any("Oracle" in path.name for path in paths)


def test_build_attack_paths_upgrade_chain() -> None:
    context = ThreatSurfaceContext(
        target_address="0x742d35cc6634c0532925a3b844bc9e7595f0beb0",
        is_upgradeable=True,
        proxy_type="transparent",
        admin_address="0x1234567890123456789012345678901234567890",
        wallet_owner="0xabcdefabcdefabcdefabcdefabcdefabcdefabcd",
        governance_protocols=[{"name": "Governor Bravo", "confidence": 92}],
    )
    dependencies = analyze_external_dependencies(context)
    boundaries = detect_trust_boundaries(context)
    privileged = analyze_privileged_entities(context)
    paths = build_attack_paths(context, dependencies, boundaries, privileged)
    assert any("Upgrade" in path.name or "ProxyAdmin" in " ".join(path.steps) for path in paths)


def test_build_attack_paths_honeypot_path() -> None:
    context = ThreatSurfaceContext(
        target_address="0x742d35cc6634c0532925a3b844bc9e7595f0beb0",
        honeypot_is_confirmed=True,
    )
    paths = build_attack_paths(context, [], [], [])
    assert any("Exit Block" in " ".join(path.steps) for path in paths)
