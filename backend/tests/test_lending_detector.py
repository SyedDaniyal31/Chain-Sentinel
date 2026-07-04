"""Lending detector unit tests (M6.1)."""

from app.blockchain.protocol.lending_detector import detect_lending
from app.blockchain.protocol.models import ProtocolDetectionContext


def test_detect_aave_from_bytecode() -> None:
    bytecode = (
        b"\x60\x80"
        + bytes.fromhex("617ba037")
        + bytes.fromhex("a415143d")
        + bytes.fromhex("35ea6a75")
    )
    context = ProtocolDetectionContext(
        target_address="0x0000000000000000000000000000000000000001",
        bytecode=bytecode,
        logic_bytecode=bytecode,
    )
    results = detect_lending(context)
    assert any(item.name == "Aave" and item.role == "pool" for item in results)


def test_detect_compound_from_bytecode() -> None:
    bytecode = (
        b"\x60\x80"
        + bytes.fromhex("a0712d68")
        + bytes.fromhex("db006a75")
        + bytes.fromhex("182df0f5")
    )
    context = ProtocolDetectionContext(
        target_address="0x0000000000000000000000000000000000000002",
        bytecode=bytecode,
        logic_bytecode=bytecode,
    )
    results = detect_lending(context)
    assert any(item.name == "Compound" and item.role == "market" for item in results)


def test_detect_lending_from_registry_deployment() -> None:
    context = ProtocolDetectionContext(
        target_address="0x87870bca3f3fd6335c3f4ce8392d69350b4fa4e2",
        bytecode=b"\x60\x80",
        logic_bytecode=b"\x60\x80",
        chain_id=1,
    )
    results = detect_lending(context)
    assert any(item.name == "Aave" and item.confidence >= 90 for item in results)


def test_detect_spark_from_source_markers() -> None:
    bytecode = b"\x60\x80" + bytes.fromhex("617ba037") + bytes.fromhex("a415143d")
    context = ProtocolDetectionContext(
        target_address="0x0000000000000000000000000000000000000003",
        bytecode=bytecode,
        logic_bytecode=bytecode,
        verified_source_code="contract SparkLendPool is LendingPool {}",
    )
    results = detect_lending(context)
    assert any(item.name == "Spark" for item in results)


def test_detect_morpho_from_bytecode() -> None:
    bytecode = b"\x60\x80" + bytes.fromhex("a0712d68") + bytes.fromhex("5c38449e")
    context = ProtocolDetectionContext(
        target_address="0x0000000000000000000000000000000000000004",
        bytecode=bytecode,
        logic_bytecode=bytecode,
    )
    results = detect_lending(context)
    assert any(item.name == "Morpho" for item in results)
