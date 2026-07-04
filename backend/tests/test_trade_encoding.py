"""Trade encoding and tax measurement unit tests."""

from app.blockchain.trade_encoding import compute_tax_bps, decode_amounts_out, decode_uint256


def test_compute_tax_bps_no_tax() -> None:
    assert compute_tax_bps(1_000_000, 1_000_000) == 0


def test_compute_tax_bps_fifty_percent() -> None:
    assert compute_tax_bps(1_000_000, 500_000) == 5000


def test_compute_tax_bps_ninety_nine_percent() -> None:
    assert compute_tax_bps(10_000, 100) == 9900


def test_decode_uint256() -> None:
    value = 123456789
    encoded = value.to_bytes(32, byteorder="big")
    assert decode_uint256(encoded) == value


def test_decode_amounts_out() -> None:
    # ABI-encoded dynamic uint256[]: offset=32, len=2, v0, v1
    payload = (
        (32).to_bytes(32, byteorder="big")
        + (2).to_bytes(32, byteorder="big")
        + (1000).to_bytes(32, byteorder="big")
        + (2500).to_bytes(32, byteorder="big")
    )
    assert decode_amounts_out(payload) == [1000, 2500]
