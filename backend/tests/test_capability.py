"""Capability fingerprint unit tests."""

from app.blockchain.capability import (
    BLACKLIST_SELECTORS,
    MINT_SELECTORS,
    OWNERSHIP_SELECTORS,
    PAUSE_SELECTORS,
    detect_capabilities_from_abi,
    detect_capabilities_from_bytecode,
    detect_capabilities_from_source,
)


def test_detect_capabilities_from_bytecode_mint() -> None:
    bytecode = b"\x60\x80" + next(iter(MINT_SELECTORS)) + b"\x00" * 20

    flags = detect_capabilities_from_bytecode(bytecode)

    assert flags.mint_capability is True
    assert flags.pause_capability is False


def test_detect_capabilities_from_bytecode_all_selectors() -> None:
    bytecode = (
        b"\x60\x80"
        + next(iter(MINT_SELECTORS))
        + next(iter(PAUSE_SELECTORS))
        + next(iter(BLACKLIST_SELECTORS))
        + next(iter(OWNERSHIP_SELECTORS))
    )

    flags = detect_capabilities_from_bytecode(bytecode)

    assert flags.mint_capability is True
    assert flags.pause_capability is True
    assert flags.blacklist_capability is True
    assert flags.ownership_capability is True


def test_detect_capabilities_from_bytecode_empty() -> None:
    flags = detect_capabilities_from_bytecode(b"")

    assert flags.has_any is False


def test_detect_capabilities_from_abi() -> None:
    abi = [
        {"type": "function", "name": "mint", "inputs": []},
        {"type": "function", "name": "pause", "inputs": []},
        {"type": "function", "name": "blacklist", "inputs": []},
        {"type": "function", "name": "owner", "inputs": []},
        {"type": "function", "name": "transfer", "inputs": []},
    ]

    flags = detect_capabilities_from_abi(abi)

    assert flags.mint_capability is True
    assert flags.pause_capability is True
    assert flags.blacklist_capability is True
    assert flags.ownership_capability is True


def test_detect_capabilities_from_source() -> None:
    source = """
    contract RugToken {
        function mint(address to, uint256 amount) external {}
        function pause() external {}
        function addToBlacklist(address user) external {}
        function transferOwnership(address newOwner) external {}
    }
    """

    flags = detect_capabilities_from_source(source)

    assert flags.mint_capability is True
    assert flags.pause_capability is True
    assert flags.blacklist_capability is True
    assert flags.ownership_capability is True
