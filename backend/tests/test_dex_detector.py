"""DEX detector unit tests (M6.1)."""

from app.blockchain.protocol.dex_detector import detect_dexes
from app.blockchain.protocol.models import ProtocolDetectionContext


def test_detect_uniswap_v2_pool_from_bytecode() -> None:
    bytecode = b"\x60\x80" + bytes.fromhex("0902f1ac") + bytes.fromhex("022c0d9f")
    context = ProtocolDetectionContext(
        target_address="0x0000000000000000000000000000000000000001",
        bytecode=bytecode,
        logic_bytecode=bytecode,
    )
    results = detect_dexes(context)
    assert any(item.name == "Uniswap V2" and item.role == "pool" for item in results)
    assert all(0 <= item.confidence <= 100 for item in results)


def test_detect_uniswap_v3_from_bytecode() -> None:
    bytecode = b"\x60\x80" + bytes.fromhex("3850c7bd") + bytes.fromhex("128acb08")
    context = ProtocolDetectionContext(
        target_address="0x0000000000000000000000000000000000000002",
        bytecode=bytecode,
        logic_bytecode=bytecode,
    )
    results = detect_dexes(context)
    assert any(item.name == "Uniswap V3" for item in results)


def test_detect_dex_from_registry_deployment() -> None:
    context = ProtocolDetectionContext(
        target_address="0x5c69bee701ef814a2b6a3edd4b1652cb9cc5aa6f",
        bytecode=b"\x60\x80",
        logic_bytecode=b"\x60\x80",
        chain_id=1,
    )
    results = detect_dexes(context)
    assert any(item.name == "Uniswap V2" and item.role == "factory" and item.confidence >= 90 for item in results)


def test_detect_curve_from_bytecode() -> None:
    bytecode = b"\x60\x80" + bytes.fromhex("3df02124") + bytes.fromhex("bb7b8b80")
    context = ProtocolDetectionContext(
        target_address="0x0000000000000000000000000000000000000003",
        bytecode=bytecode,
        logic_bytecode=bytecode,
    )
    results = detect_dexes(context)
    assert any(item.name == "Curve" for item in results)


def test_detect_dex_from_verified_source_markers() -> None:
    bytecode = b"\x60\x80" + bytes.fromhex("0902f1ac")
    context = ProtocolDetectionContext(
        target_address="0x0000000000000000000000000000000000000004",
        bytecode=bytecode,
        logic_bytecode=bytecode,
        is_verified=True,
        verified_source_code="contract SushiSwapPair is IUniswapV2Pair {}",
    )
    results = detect_dexes(context)
    assert any(item.name == "SushiSwap" for item in results)


def test_detect_dex_returns_empty_for_eoa() -> None:
    context = ProtocolDetectionContext(
        target_address="0x0000000000000000000000000000000000000005",
        bytecode=b"",
        logic_bytecode=b"",
    )
    assert detect_dexes(context) == []
