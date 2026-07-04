"""Proxy detector unit tests (M6.0)."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from hexbytes import HexBytes
from web3 import Web3

from app.blockchain.eip1967 import EIP1967_ADMIN_SLOT, EIP1967_IMPLEMENTATION_SLOT
from app.blockchain.protocol.models import ProtocolDetectionContext, ProtocolProxyKind
from app.blockchain.protocol.proxy_detector import (
    detect_minimal_proxy_from_bytecode,
    detect_proxy,
    detect_uups_from_logic_bytecode,
)

IMPLEMENTATION = "0xdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef"
ADMIN = "0x1234567890123456789012345678901234567890"
PROXY = "0xa231aa3388416ebc1b8f8a51b412327832524ca4"


def _address_storage_word(address: str) -> bytes:
    return b"\x00" * 12 + bytes.fromhex(address[2:])


def test_detect_minimal_proxy_from_bytecode() -> None:
    bytecode = bytes.fromhex("363d3d373d3d3d363d73") + b"\x00" * 20
    result = detect_minimal_proxy_from_bytecode(bytecode)
    assert result is not None
    assert result.proxy_kind == ProtocolProxyKind.MINIMAL_PROXY


def test_detect_uups_from_logic_bytecode() -> None:
    upgrade_to = Web3.keccak(text="upgradeTo(address)")[:4]
    assert detect_uups_from_logic_bytecode(b"\x60\x80" + upgrade_to) is True


@pytest.mark.asyncio
async def test_detect_transparent_proxy() -> None:
    class MockEth:
        async def get_storage_at(self, _address: str, slot: str) -> HexBytes:
            if slot == EIP1967_IMPLEMENTATION_SLOT:
                return HexBytes(_address_storage_word(IMPLEMENTATION))
            if slot == EIP1967_ADMIN_SLOT:
                return HexBytes(_address_storage_word(ADMIN))
            return HexBytes(b"\x00" * 32)

    web3 = MagicMock()
    web3.eth = MockEth()
    context = ProtocolDetectionContext(
        target_address=PROXY,
        bytecode=b"\x60\x80",
        logic_bytecode=b"\x60\x80",
        implementation_address=IMPLEMENTATION,
        admin_address=ADMIN,
    )

    result = await detect_proxy(web3, context)
    assert result.proxy_kind == ProtocolProxyKind.TRANSPARENT
    assert result.detected is True


@pytest.mark.asyncio
async def test_detect_no_proxy() -> None:
    class MockEth:
        async def get_storage_at(self, _address: str, _slot: str) -> HexBytes:
            return HexBytes(b"\x00" * 32)

    web3 = MagicMock()
    web3.eth = MockEth()
    context = ProtocolDetectionContext(
        target_address=PROXY,
        bytecode=b"\x60\x80",
        logic_bytecode=b"\x60\x80",
    )

    result = await detect_proxy(web3, context)
    assert result.proxy_kind == ProtocolProxyKind.NONE
    assert result.detected is False
