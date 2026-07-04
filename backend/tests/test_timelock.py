"""Timelock helper unit tests."""

from app.blockchain.timelock import parse_min_delay


def test_parse_min_delay_zero() -> None:
    assert parse_min_delay(b"\x00" * 32) == 0
