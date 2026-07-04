"""TimelockAnalyzer unit tests."""

from unittest.mock import MagicMock

import pytest

from app.blockchain.timelock import GET_MIN_DELAY_SELECTOR, parse_min_delay
from app.schemas.scan_result import TimelockAnalysisData
from app.services.timelock_analyzer import TimelockAnalyzer

TIMELOCK = "0xabcdefabcdefabcdefabcdefabcdefabcdefabcd"


def _min_delay_return(seconds: int) -> bytes:
    return seconds.to_bytes(32, byteorder="big")


def test_parse_min_delay_decodes_uint256() -> None:
    assert parse_min_delay(_min_delay_return(86400)) == 86400


def _build_mock_web3(*, min_delay_by_address: dict[str, int] | None = None) -> MagicMock:
    delays = {address.lower(): delay for address, delay in (min_delay_by_address or {}).items()}

    class MockEth:
        async def call(self, transaction: dict[str, str]) -> bytes:
            assert transaction["data"] == GET_MIN_DELAY_SELECTOR
            delay = delays.get(transaction["to"].lower(), 86400)
            return _min_delay_return(delay)

    web3 = MagicMock()
    web3.eth = MockEth()
    return web3


@pytest.mark.asyncio
async def test_timelock_analyzer_detects_timelock_controller() -> None:
    analyzer = TimelockAnalyzer(_build_mock_web3(min_delay_by_address={TIMELOCK: 172800}))

    result = await analyzer.analyze(TIMELOCK)

    assert result == TimelockAnalysisData(is_timelock=True, min_delay=172800)


@pytest.mark.asyncio
async def test_timelock_analyzer_returns_false_when_call_reverts() -> None:
    web3 = MagicMock()

    async def fail(*_args: object, **_kwargs: object) -> bytes:
        raise RuntimeError("execution reverted")

    web3.eth.call = fail
    analyzer = TimelockAnalyzer(web3)

    result = await analyzer.analyze(TIMELOCK)

    assert result == TimelockAnalysisData(is_timelock=False, min_delay=None)
