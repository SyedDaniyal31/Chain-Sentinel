"""AdminClassifier unit tests."""

from unittest.mock import MagicMock

import pytest
from hexbytes import HexBytes

from app.blockchain.multisig import GET_OWNERS_SELECTOR, GET_THRESHOLD_SELECTOR
from app.core.exceptions import BlockchainRpcError
from app.models.enums import AdminType
from app.services.admin_classifier import AdminClassifier

ADMIN_EOA = "0x1234567890123456789012345678901234567890"
ADMIN_CONTRACT = "0xabcdefabcdefabcdefabcdefabcdefabcdefabcd"


def _gnosis_safe_bytecode() -> bytes:
    return b"\x60\x80" + GET_OWNERS_SELECTOR + b"\x00" * 10 + GET_THRESHOLD_SELECTOR


def _build_mock_web3(*, code_by_address: dict[str, bytes] | None = None) -> MagicMock:
    codes = {address.lower(): code for address, code in (code_by_address or {}).items()}

    class MockEth:
        async def get_code(self, address: str) -> HexBytes:
            return HexBytes(codes.get(address.lower(), b""))

    web3 = MagicMock()
    web3.eth = MockEth()
    return web3


@pytest.mark.asyncio
async def test_admin_classifier_returns_none_without_admin() -> None:
    classifier = AdminClassifier(_build_mock_web3())

    assert await classifier.classify(None) is None


@pytest.mark.asyncio
async def test_admin_classifier_detects_eoa() -> None:
    classifier = AdminClassifier(_build_mock_web3())

    assert await classifier.classify(ADMIN_EOA) == AdminType.EOA


@pytest.mark.asyncio
async def test_admin_classifier_detects_contract() -> None:
    classifier = AdminClassifier(
        _build_mock_web3(code_by_address={ADMIN_CONTRACT: b"\x60\x80\x60\x40"})
    )

    assert await classifier.classify(ADMIN_CONTRACT) == AdminType.CONTRACT


@pytest.mark.asyncio
async def test_admin_classifier_detects_multisig() -> None:
    classifier = AdminClassifier(
        _build_mock_web3(code_by_address={ADMIN_CONTRACT: _gnosis_safe_bytecode()})
    )

    assert await classifier.classify(ADMIN_CONTRACT) == AdminType.MULTISIG


@pytest.mark.asyncio
async def test_admin_classifier_raises_on_rpc_failure() -> None:
    web3 = MagicMock()

    async def fail(*_args: object, **_kwargs: object) -> HexBytes:
        raise ConnectionError("rpc down")

    web3.eth.get_code = fail
    classifier = AdminClassifier(web3)

    with pytest.raises(BlockchainRpcError, match="admin classification request failed"):
        await classifier.classify(ADMIN_EOA)
