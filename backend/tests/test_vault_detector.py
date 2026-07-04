"""Vault detector unit tests (M6.2)."""

from app.blockchain.protocol.models import ProtocolDetectionContext
from app.blockchain.protocol.standards_detector import (
    ERC4626_ASSET_SELECTOR,
    ERC4626_DEPOSIT_SELECTOR,
    ERC4626_TOTAL_ASSETS_SELECTOR,
)
from app.blockchain.protocol.vault_detector import detect_vaults


def test_detect_erc4626_vault_from_bytecode() -> None:
    bytecode = (
        b"\x60\x80"
        + ERC4626_ASSET_SELECTOR
        + ERC4626_TOTAL_ASSETS_SELECTOR
        + ERC4626_DEPOSIT_SELECTOR
    )
    context = ProtocolDetectionContext(
        target_address="0x0000000000000000000000000000000000000001",
        bytecode=bytecode,
        logic_bytecode=bytecode,
    )
    results = detect_vaults(context)
    assert any(item.name == "ERC4626" and item.type == "ERC4626 Vault" for item in results)


def test_detect_yearn_from_registry() -> None:
    context = ProtocolDetectionContext(
        target_address="0x5f18c75abdae578b483e0628919e8f13bd7f7d0a",
        bytecode=b"\x60\x80",
        logic_bytecode=b"\x60\x80",
        chain_id=1,
    )
    results = detect_vaults(context)
    assert any(item.name == "Yearn" and item.confidence >= 90 for item in results)


def test_detect_beefy_from_source() -> None:
    bytecode = b"\x60\x80" + bytes.fromhex("a694fc3a") + ERC4626_DEPOSIT_SELECTOR
    context = ProtocolDetectionContext(
        target_address="0x0000000000000000000000000000000000000002",
        bytecode=bytecode,
        logic_bytecode=bytecode,
        verified_source_code="contract BeefyVault is IStrategy {}",
    )
    results = detect_vaults(context)
    assert any(item.name == "Beefy" for item in results)


def test_detect_eigenlayer_from_source() -> None:
    bytecode = b"\x60\x80" + bytes.fromhex("7b47c653")
    context = ProtocolDetectionContext(
        target_address="0x0000000000000000000000000000000000000003",
        bytecode=bytecode,
        logic_bytecode=bytecode,
        verified_source_code="contract StrategyManager is EigenLayer {}",
    )
    results = detect_vaults(context)
    assert any(item.name == "EigenLayer" for item in results)
