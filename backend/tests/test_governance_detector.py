"""Governance detector unit tests (M6.2)."""

from app.blockchain.protocol.governance_detector import detect_governance
from app.blockchain.protocol.models import ProtocolDetectionContext


def test_detect_governor_bravo_from_bytecode() -> None:
    bytecode = (
        b"\x60\x80"
        + bytes.fromhex("0121a88c")
        + bytes.fromhex("56781388")
        + bytes.fromhex("160eed98")
        + bytes.fromhex("fe0d94c1")
    )
    context = ProtocolDetectionContext(
        target_address="0x0000000000000000000000000000000000000001",
        bytecode=bytecode,
        logic_bytecode=bytecode,
    )
    results = detect_governance(context)
    assert any(item.name == "Governor Bravo" for item in results)


def test_detect_governor_bravo_from_registry() -> None:
    context = ProtocolDetectionContext(
        target_address="0x30948667925aaad57af76230dada8050db471066",
        bytecode=b"\x60\x80",
        logic_bytecode=b"\x60\x80",
        chain_id=1,
    )
    results = detect_governance(context)
    assert any(item.name == "Governor Bravo" and item.confidence >= 90 for item in results)


def test_detect_openzeppelin_governor_from_source() -> None:
    bytecode = b"\x60\x80" + bytes.fromhex("0121a88c") + bytes.fromhex("56781388")
    context = ProtocolDetectionContext(
        target_address="0x0000000000000000000000000000000000000002",
        bytecode=bytecode,
        logic_bytecode=bytecode,
        verified_source_code="contract TokenGovernor is Governor, OpenZeppelin Governor {}",
    )
    results = detect_governance(context)
    assert any(item.name == "OpenZeppelin Governor" for item in results)


def test_detect_timelock_governor_from_source() -> None:
    bytecode = b"\x60\x80" + bytes.fromhex("f2a0ba21") + bytes.fromhex("fe0d94c1")
    context = ProtocolDetectionContext(
        target_address="0x0000000000000000000000000000000000000003",
        bytecode=bytecode,
        logic_bytecode=bytecode,
        verified_source_code="contract TimelockGovernor is TimelockController {}",
    )
    results = detect_governance(context)
    assert any(item.name == "Timelock Governor" for item in results)
