"""Bridge detector unit tests (M6.2)."""

from app.blockchain.protocol.bridge_detector import detect_bridges
from app.blockchain.protocol.models import ProtocolDetectionContext


def test_detect_layerzero_from_registry() -> None:
    context = ProtocolDetectionContext(
        target_address="0x66a71dcef29a0ffbdb3c6a460a3b5bc2251575",
        bytecode=b"\x60\x80",
        logic_bytecode=b"\x60\x80",
        chain_id=1,
    )
    results = detect_bridges(context)
    assert any(item.name == "LayerZero" and item.role == "endpoint" and item.confidence >= 90 for item in results)


def test_detect_wormhole_from_bytecode() -> None:
    bytecode = b"\x60\x80" + bytes.fromhex("b8e6c081") + bytes.fromhex("6a761202")
    context = ProtocolDetectionContext(
        target_address="0x0000000000000000000000000000000000000001",
        bytecode=bytecode,
        logic_bytecode=bytecode,
    )
    results = detect_bridges(context)
    assert any(item.name == "Wormhole" for item in results)


def test_detect_stargate_from_source() -> None:
    bytecode = b"\x60\x80" + bytes.fromhex("c4d66de8")
    context = ProtocolDetectionContext(
        target_address="0x0000000000000000000000000000000000000002",
        bytecode=bytecode,
        logic_bytecode=bytecode,
        verified_source_code="contract StargateRouter is IStargate {}",
    )
    results = detect_bridges(context)
    assert any(item.name == "Stargate" for item in results)


def test_detect_circle_cctp_from_bytecode() -> None:
    bytecode = b"\x60\x80" + bytes.fromhex("6fd3504e") + bytes.fromhex("57ecfd28")
    context = ProtocolDetectionContext(
        target_address="0x0000000000000000000000000000000000000003",
        bytecode=bytecode,
        logic_bytecode=bytecode,
    )
    results = detect_bridges(context)
    assert any(item.name == "Circle CCTP" for item in results)


def test_detect_bridge_returns_empty_for_eoa() -> None:
    context = ProtocolDetectionContext(
        target_address="0x0000000000000000000000000000000000000004",
        bytecode=b"",
        logic_bytecode=b"",
    )
    assert detect_bridges(context) == []
