"""Oracle detector unit tests (M6.1)."""

from app.blockchain.protocol.models import ProtocolDetectionContext
from app.blockchain.protocol.oracle_detector import detect_oracles


def test_detect_chainlink_from_bytecode() -> None:
    bytecode = (
        b"\x60\x80"
        + bytes.fromhex("50d25bcd")
        + bytes.fromhex("feaf968c")
        + bytes.fromhex("7284e416")
    )
    context = ProtocolDetectionContext(
        target_address="0x0000000000000000000000000000000000000001",
        bytecode=bytecode,
        logic_bytecode=bytecode,
    )
    results = detect_oracles(context)
    assert any(item.name == "Chainlink" for item in results)
    assert all(0 <= item.confidence <= 100 for item in results)


def test_detect_pyth_from_bytecode() -> None:
    bytecode = b"\x60\x80" + bytes.fromhex("9d15dcc8") + bytes.fromhex("6cc43823")
    context = ProtocolDetectionContext(
        target_address="0x0000000000000000000000000000000000000002",
        bytecode=bytecode,
        logic_bytecode=bytecode,
    )
    results = detect_oracles(context)
    assert any(item.name == "Pyth" for item in results)


def test_detect_redstone_from_source_markers() -> None:
    bytecode = b"\x60\x80" + bytes.fromhex("3b8745f9")
    context = ProtocolDetectionContext(
        target_address="0x0000000000000000000000000000000000000003",
        bytecode=bytecode,
        logic_bytecode=bytecode,
        verified_source_code="contract RedstoneOracleAdapter is DataFeed {}",
    )
    results = detect_oracles(context)
    assert any(item.name == "Redstone" for item in results)


def test_detect_oracle_returns_empty_for_eoa() -> None:
    context = ProtocolDetectionContext(
        target_address="0x0000000000000000000000000000000000000004",
        bytecode=b"",
        logic_bytecode=b"",
    )
    assert detect_oracles(context) == []
