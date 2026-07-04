"""ProxyAdminAnalyzer unit tests."""

from unittest.mock import MagicMock

import pytest
from hexbytes import HexBytes

from app.blockchain.ownable import OWNER_FUNCTION_SELECTOR
from app.models.enums import AdminType
from app.schemas.scan_result import ProxyAdminOwnerAnalysisData
from app.services.proxy_admin_analyzer import ProxyAdminAnalyzer

PROXY_ADMIN = "0xabcdefabcdefabcdefabcdefabcdefabcdefabcd"
OWNER_EOA = "0x1234567890123456789012345678901234567890"


def _owner_return_data(address: str) -> bytes:
    return b"\x00" * 12 + bytes.fromhex(address[2:])


def _build_mock_web3(
    *,
    owner_by_admin: dict[str, bytes] | None = None,
    code_by_address: dict[str, bytes] | None = None,
    call_should_fail: bool = False,
) -> MagicMock:
    owners = {address.lower(): data for address, data in (owner_by_admin or {}).items()}
    codes = {address.lower(): code for address, code in (code_by_address or {}).items()}

    class MockEth:
        async def call(self, transaction: dict[str, str]) -> bytes:
            if call_should_fail:
                raise RuntimeError("execution reverted")
            to_address = transaction["to"].lower()
            assert transaction["data"] == OWNER_FUNCTION_SELECTOR
            return owners.get(to_address, b"\x00" * 32)

        async def get_code(self, address: str) -> HexBytes:
            return HexBytes(codes.get(address.lower(), b""))

    web3 = MagicMock()
    web3.eth = MockEth()
    return web3


@pytest.mark.asyncio
async def test_proxy_admin_analyzer_skips_eoa_admin() -> None:
    analyzer = ProxyAdminAnalyzer(_build_mock_web3())

    result = await analyzer.analyze(OWNER_EOA, AdminType.EOA)

    assert result == ProxyAdminOwnerAnalysisData(owner_address=None, owner_type=None)


@pytest.mark.asyncio
async def test_proxy_admin_analyzer_skips_multisig_admin() -> None:
    analyzer = ProxyAdminAnalyzer(_build_mock_web3())

    result = await analyzer.analyze(PROXY_ADMIN, AdminType.MULTISIG)

    assert result == ProxyAdminOwnerAnalysisData(owner_address=None, owner_type=None)


@pytest.mark.asyncio
async def test_proxy_admin_analyzer_resolves_owner_eoa() -> None:
    analyzer = ProxyAdminAnalyzer(
        _build_mock_web3(
            owner_by_admin={PROXY_ADMIN: _owner_return_data(OWNER_EOA)},
            code_by_address={OWNER_EOA: b""},
        )
    )

    result = await analyzer.analyze(PROXY_ADMIN, AdminType.CONTRACT)

    assert result.owner_address == OWNER_EOA
    assert result.owner_type == AdminType.EOA


@pytest.mark.asyncio
async def test_proxy_admin_analyzer_returns_none_when_owner_call_reverts() -> None:
    analyzer = ProxyAdminAnalyzer(_build_mock_web3(call_should_fail=True))

    result = await analyzer.analyze(PROXY_ADMIN, AdminType.CONTRACT)

    assert result == ProxyAdminOwnerAnalysisData(owner_address=None, owner_type=None)


@pytest.mark.asyncio
async def test_proxy_admin_analyzer_returns_none_for_zero_owner() -> None:
    analyzer = ProxyAdminAnalyzer(
        _build_mock_web3(owner_by_admin={PROXY_ADMIN: b"\x00" * 32})
    )

    result = await analyzer.analyze(PROXY_ADMIN, AdminType.CONTRACT)

    assert result == ProxyAdminOwnerAnalysisData(owner_address=None, owner_type=None)
