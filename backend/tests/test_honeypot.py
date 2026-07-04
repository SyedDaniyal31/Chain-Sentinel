"""Honeypot fingerprint unit tests."""

from app.blockchain.honeypot import (
    BLACKLIST_PROBE_SELECTORS,
    SELL_RESTRICTION_SELECTORS,
    TRADING_ENABLED_SELECTORS,
    TRANSFER_TAX_SELECTORS,
    WHITELIST_SELECTORS,
    detect_honeypot_from_abi,
    detect_honeypot_from_bytecode,
    detect_honeypot_from_source,
    merge_honeypot_flags,
)
from app.blockchain.honeypot_simulation import HoneypotSimulationResult


def test_detect_honeypot_from_bytecode_trading_control() -> None:
    bytecode = b"\x60\x80" + next(iter(TRADING_ENABLED_SELECTORS))

    flags = detect_honeypot_from_bytecode(bytecode)

    assert flags.trading_enabled_control is True
    assert flags.whitelist_control is False


def test_detect_honeypot_from_bytecode_blacklist_sell_blocking() -> None:
    bytecode = (
        b"\x60\x80"
        + next(iter(BLACKLIST_PROBE_SELECTORS))
        + next(iter(SELL_RESTRICTION_SELECTORS))
    )

    flags = detect_honeypot_from_bytecode(bytecode)

    assert flags.blacklist_sell_blocking is True


def test_detect_honeypot_from_bytecode_blacklist_alone_not_sell_blocking() -> None:
    bytecode = b"\x60\x80" + bytes.fromhex("fe575a87")  # isBlacklisted(address)

    flags = detect_honeypot_from_bytecode(bytecode)

    assert flags.blacklist_sell_blocking is False


def test_detect_honeypot_from_bytecode_all_indicators() -> None:
    bytecode = (
        b"\x60\x80"
        + next(iter(TRADING_ENABLED_SELECTORS))
        + next(iter(WHITELIST_SELECTORS))
        + next(iter(BLACKLIST_PROBE_SELECTORS))
        + next(iter(SELL_RESTRICTION_SELECTORS))
        + next(iter(TRANSFER_TAX_SELECTORS))
    )

    flags = detect_honeypot_from_bytecode(bytecode)

    assert flags.trading_enabled_control is True
    assert flags.whitelist_control is True
    assert flags.blacklist_sell_blocking is True
    assert flags.transfer_tax_control is True


def test_detect_honeypot_from_abi() -> None:
    abi = [
        {"type": "function", "name": "enableTrading", "inputs": []},
        {"type": "function", "name": "isWhitelisted", "inputs": []},
        {"type": "function", "name": "isBlacklisted", "inputs": []},
        {"type": "function", "name": "setMaxSellAmount", "inputs": []},
        {"type": "function", "name": "setSellFee", "inputs": []},
    ]

    flags = detect_honeypot_from_abi(abi)

    assert flags.trading_enabled_control is True
    assert flags.whitelist_control is True
    assert flags.blacklist_sell_blocking is True
    assert flags.transfer_tax_control is True


def test_detect_honeypot_from_source() -> None:
    source = """
    contract HoneypotToken {
        function enableTrading() external {}
        function addToWhitelist(address user) external {}
        function isBot(address user) external view returns (bool) {}
        function setMaxTxAmount(uint256 amount) external {}
        function setBuyFee(uint256 fee) external {}
    }
    """

    flags = detect_honeypot_from_source(source)

    assert flags.trading_enabled_control is True
    assert flags.whitelist_control is True
    assert flags.blacklist_sell_blocking is True
    assert flags.transfer_tax_control is True


def test_simulation_result_maps_sell_block_to_flags() -> None:
    result = HoneypotSimulationResult(can_sell=False, simulated=True)

    flags = result.to_honeypot_flags()

    assert flags.blacklist_sell_blocking is True


def test_merge_honeypot_flags_combines_sources() -> None:
    heuristic = detect_honeypot_from_bytecode(
        b"\x60\x80" + next(iter(TRADING_ENABLED_SELECTORS))
    )
    simulated = HoneypotSimulationResult(can_sell=False, simulated=True).to_honeypot_flags()

    merged = merge_honeypot_flags(heuristic, simulated)

    assert merged.trading_enabled_control is True
    assert merged.blacklist_sell_blocking is True
