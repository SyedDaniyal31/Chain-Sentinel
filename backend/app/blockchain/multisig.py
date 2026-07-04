"""Heuristics for identifying multisig wallet bytecode on-chain."""

# Gnosis Safe (and compatible) function selectors present in runtime bytecode.
GET_OWNERS_SELECTOR = bytes.fromhex("a0e67e2b")
GET_THRESHOLD_SELECTOR = bytes.fromhex("e75235b8")


def is_gnosis_safe_multisig(bytecode: bytes) -> bool:
    """
    Return True when bytecode exposes Gnosis Safe-style owner/threshold accessors.

    This is a heuristic — other multisig patterns may classify as CONTRACT until
    dedicated fingerprinting is added.
    """
    return GET_OWNERS_SELECTOR in bytecode and GET_THRESHOLD_SELECTOR in bytecode
