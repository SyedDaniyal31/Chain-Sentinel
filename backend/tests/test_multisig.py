"""Multisig bytecode heuristic tests."""

from app.blockchain.multisig import (
    GET_OWNERS_SELECTOR,
    GET_THRESHOLD_SELECTOR,
    is_gnosis_safe_multisig,
)


def test_is_gnosis_safe_multisig_detects_safe_bytecode() -> None:
    bytecode = b"\x60\x80" + GET_OWNERS_SELECTOR + b"\x00" * 8 + GET_THRESHOLD_SELECTOR

    assert is_gnosis_safe_multisig(bytecode) is True


def test_is_gnosis_safe_multisig_rejects_plain_contract() -> None:
    assert is_gnosis_safe_multisig(b"\x60\x80\x60\x40") is False


def test_is_gnosis_safe_multisig_requires_both_selectors() -> None:
    assert is_gnosis_safe_multisig(GET_OWNERS_SELECTOR + b"\x00" * 20) is False
