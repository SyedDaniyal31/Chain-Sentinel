"""M6.2 protocol aggregation, confidence, and legacy compatibility tests."""

from app.blockchain.protocol.confidence_engine import compute_confidence
from app.blockchain.protocol.models import (
    BridgeDetectionResult,
    DexDetectionResult,
    GovernanceDetectionResult,
    NftDetectionResult,
    ProtocolDetectionBundle,
    StandardDetection,
    VaultDetectionResult,
    ProtocolStandard,
)
from app.blockchain.protocol.protocol_detector import build_detection_reasons, resolve_protocol_identity
from app.models.enums import ConfidenceLevel
from app.schemas.scan_result import ProtocolIntelligenceData


def test_resolve_protocol_identity_bridge_family() -> None:
    bundle = ProtocolDetectionBundle(
        bridges=[BridgeDetectionResult(name="LayerZero", role="endpoint", confidence=94)],
    )
    family, name, _ = resolve_protocol_identity(bundle)
    assert family.value == "bridge"
    assert name == "layerzero_endpoint"


def test_resolve_protocol_identity_vault_family() -> None:
    bundle = ProtocolDetectionBundle(
        vaults=[VaultDetectionResult(name="Yearn", type="ERC4626 Vault", confidence=95)],
    )
    family, name, _ = resolve_protocol_identity(bundle)
    assert family.value == "vault"
    assert name == "yearn_vault"


def test_resolve_protocol_identity_nft_marketplace() -> None:
    bundle = ProtocolDetectionBundle(
        nfts=[NftDetectionResult(standard="ERC721", marketplace="OpenSea", confidence=90)],
    )
    family, name, _ = resolve_protocol_identity(bundle)
    assert family.value == "nft"
    assert name == "opensea_nft"


def test_resolve_protocol_identity_governance() -> None:
    bundle = ProtocolDetectionBundle(
        governance=[GovernanceDetectionResult(name="Governor Bravo", confidence=92)],
    )
    family, name, _ = resolve_protocol_identity(bundle)
    assert family.value == "governance"
    assert name == "governor_bravo"


def test_m62_confidence_includes_infrastructure_evidence() -> None:
    baseline = compute_confidence(
        ProtocolDetectionBundle(
            standards=[
                StandardDetection(
                    standard=ProtocolStandard.ERC20,
                    detected=True,
                    reason="erc20",
                    confidence="high",
                )
            ],
            detection_reasons=["erc20"],
        )
    )
    enriched = compute_confidence(
        ProtocolDetectionBundle(
            standards=[
                StandardDetection(
                    standard=ProtocolStandard.ERC20,
                    detected=True,
                    reason="erc20",
                    confidence="high",
                )
            ],
            bridges=[BridgeDetectionResult(name="LayerZero", role="endpoint", confidence=94)],
            vaults=[VaultDetectionResult(name="Yearn", type="ERC4626 Vault", confidence=95)],
            nfts=[NftDetectionResult(standard="ERC721", marketplace="OpenSea", confidence=90)],
            governance=[GovernanceDetectionResult(name="Governor Bravo", confidence=92)],
            detection_reasons=["erc20"],
        )
    )
    assert enriched.score > baseline.score
    assert enriched.level in {ConfidenceLevel.MEDIUM.value, ConfidenceLevel.HIGH.value}


def test_build_detection_reasons_includes_m62_entries() -> None:
    bundle = ProtocolDetectionBundle(
        bridges=[BridgeDetectionResult(name="Hyperlane", role="mailbox", confidence=88)],
        vaults=[VaultDetectionResult(name="Pendle", type="Yield Token", confidence=85)],
        nfts=[NftDetectionResult(standard="ERC1155", marketplace="", confidence=80)],
        governance=[GovernanceDetectionResult(name="Compound Governor", confidence=90)],
    )
    reasons = build_detection_reasons(bundle)
    assert any("Bridge detected: Hyperlane" in reason for reason in reasons)
    assert any("Vault detected: Pendle" in reason for reason in reasons)
    assert any("NFT detected:" in reason for reason in reasons)
    assert any("Governance detected: Compound Governor" in reason for reason in reasons)


def test_legacy_protocol_intelligence_without_m62_fields() -> None:
    payload = ProtocolIntelligenceData.model_validate(
        {
            "protocol_family": "token",
            "protocol_name": "erc20_token",
            "standards": ["ERC20"],
            "confidence": "medium",
            "dexes": [{"name": "Uniswap V2", "role": "pool", "confidence": 80}],
        }
    )
    assert payload.bridges == []
    assert payload.vaults == []
    assert payload.nfts == []
    assert payload.governance == []
    assert payload.confidence.level.value == "medium"
    assert payload.dexes[0].name == "Uniswap V2"


def test_dex_priority_below_bridge_in_family_resolution() -> None:
    bundle = ProtocolDetectionBundle(
        bridges=[BridgeDetectionResult(name="Wormhole", role="core", confidence=90)],
        dexes=[DexDetectionResult(name="Uniswap V3", role="pool", confidence=95)],
    )
    family, name, _ = resolve_protocol_identity(bundle)
    assert family.value == "bridge"
    assert name == "wormhole_core"
