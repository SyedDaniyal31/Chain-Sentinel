"""Protocol detector and registry unit tests (M6.0)."""

from app.blockchain.multisig import GET_OWNERS_SELECTOR, GET_THRESHOLD_SELECTOR
from app.blockchain.protocol.models import (
    FrameworkDetection,
    ProtocolDetectionBundle,
    ProtocolFramework,
    ProtocolProxyKind,
    ProtocolStandard,
    ProxyDetection,
    StandardDetection,
)
from app.blockchain.protocol.protocol_detector import resolve_protocol_identity, resolve_confidence
from app.blockchain.protocol.protocol_registry import detect_integrations
from app.blockchain.token_standards import ERC20_BALANCE_OF_SELECTOR, ERC20_TRANSFER_SELECTOR, ERC20_TOTAL_SUPPLY_SELECTOR
from app.models.enums import ConfidenceLevel


def test_resolve_protocol_identity_erc20() -> None:
    bundle = ProtocolDetectionBundle(
        standards=[
            StandardDetection(
                standard=ProtocolStandard.ERC20,
                detected=True,
                reason="erc20",
                confidence="high",
            )
        ]
    )
    family, name, protocol_type = resolve_protocol_identity(bundle)
    assert family.value == "token"
    assert name == "erc20_token"
    assert protocol_type.value == "fungible_token"


def test_resolve_protocol_identity_transparent_proxy() -> None:
    bundle = ProtocolDetectionBundle(
        proxy=ProxyDetection(
            proxy_kind=ProtocolProxyKind.TRANSPARENT,
            detected=True,
            reason="transparent",
            confidence="high",
        )
    )
    family, name, protocol_type = resolve_protocol_identity(bundle)
    assert family.value == "proxy"
    assert name == "transparent_proxy"


def test_resolve_confidence_high_with_multiple_signals() -> None:
    bundle = ProtocolDetectionBundle(
        standards=[
            StandardDetection(
                standard=ProtocolStandard.ERC20,
                detected=True,
                reason="erc20",
                confidence="high",
            )
        ],
        frameworks=[
            FrameworkDetection(
                framework=ProtocolFramework.OPENZEPPELIN_OWNABLE,
                detected=True,
                reason="ownable",
                confidence="high",
            )
        ],
        detection_reasons=["erc20", "ownable"],
    )
    assert resolve_confidence(bundle) == ConfidenceLevel.HIGH


def test_detect_gnosis_safe_integration() -> None:
    bytecode = b"\x60\x80" + GET_OWNERS_SELECTOR + GET_THRESHOLD_SELECTOR
    integrations = detect_integrations(bytecode)
    assert "Gnosis Safe" in integrations


def test_detect_uniswap_pair_integration() -> None:
    bytecode = b"\x60\x80" + bytes.fromhex("0902f1ac") + bytes.fromhex("022c0d9f")
    integrations = detect_integrations(bytecode)
    assert "Uniswap V2 Pair" in integrations
