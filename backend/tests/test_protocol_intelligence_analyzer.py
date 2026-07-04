"""ProtocolIntelligenceAnalyzer integration tests (M6.0)."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from hexbytes import HexBytes
from web3 import Web3

from app.blockchain.eip1967 import EIP1967_ADMIN_SLOT, EIP1967_IMPLEMENTATION_SLOT
from app.blockchain.token_standards import ERC20_BALANCE_OF_SELECTOR, ERC20_TOTAL_SUPPLY_SELECTOR, ERC20_TRANSFER_SELECTOR
from app.models.enums import ConfidenceLevel
from app.services.protocol_intelligence_analyzer import ProtocolIntelligenceAnalyzer

IMPLEMENTATION = "0xdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef"
ADMIN = "0x1234567890123456789012345678901234567890"
PROXY = "0xa231aa3388416ebc1b8f8a51b412327832524ca4"


def _address_storage_word(address: str) -> bytes:
    return b"\x00" * 12 + bytes.fromhex(address[2:])


def _build_mock_web3(*, storage_slots: dict[str, bytes] | None = None) -> MagicMock:
    slots = storage_slots or {}

    class MockEth:
        async def get_storage_at(self, _address: str, slot: str) -> HexBytes:
            return HexBytes(slots.get(slot, b"\x00" * 32))

    web3 = MagicMock()
    web3.eth = MockEth()
    return web3


@pytest.mark.asyncio
async def test_protocol_intelligence_analyzer_erc20_proxy() -> None:
    logic_bytecode = b"\x60\x80" + ERC20_TRANSFER_SELECTOR + ERC20_BALANCE_OF_SELECTOR + ERC20_TOTAL_SUPPLY_SELECTOR
    ownable_owner = Web3.keccak(text="owner()")[:4]
    ownable_transfer = Web3.keccak(text="transferOwnership(address)")[:4]
    logic_bytecode += ownable_owner + ownable_transfer

    storage_slots = {
        EIP1967_IMPLEMENTATION_SLOT: _address_storage_word(IMPLEMENTATION),
        EIP1967_ADMIN_SLOT: _address_storage_word(ADMIN),
    }
    analyzer = ProtocolIntelligenceAnalyzer(_build_mock_web3(storage_slots=storage_slots))

    result = await analyzer.analyze(
        PROXY,
        bytecode=b"\x60\x80",
        implementation_bytecode=logic_bytecode,
        implementation_address=IMPLEMENTATION,
        admin_address=ADMIN,
        is_verified=True,
    )

    assert result.protocol_family == "token"
    assert result.protocol_name == "erc20_token"
    assert "ERC20" in result.standards
    assert "OpenZeppelin Ownable" in result.frameworks
    assert result.proxy_type == "transparent"
    assert result.confidence.level in {ConfidenceLevel.MEDIUM, ConfidenceLevel.HIGH}
    assert result.confidence.score >= 40
    assert result.detection_reasons


@pytest.mark.asyncio
async def test_protocol_intelligence_analyzer_empty_for_eoa() -> None:
    analyzer = ProtocolIntelligenceAnalyzer(_build_mock_web3())
    result = await analyzer.analyze(PROXY, bytecode=b"")
    assert result.protocol_name == "unknown"
    assert result.standards == []
