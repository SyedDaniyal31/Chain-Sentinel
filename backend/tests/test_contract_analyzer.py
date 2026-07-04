"""ContractAnalyzer unit tests."""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest
from hexbytes import HexBytes

from app.blockchain.capability import MINT_SELECTORS, PAUSE_SELECTORS
from app.blockchain.eip1967 import EIP1967_ADMIN_SLOT, EIP1967_IMPLEMENTATION_SLOT
from app.blockchain.honeypot import (
    BLACKLIST_PROBE_SELECTORS,
    SELL_RESTRICTION_SELECTORS,
    TRADING_ENABLED_SELECTORS,
)
from app.blockchain.erc165 import SUPPORTS_INTERFACE_SELECTOR
from app.blockchain.multisig import GET_OWNERS_SELECTOR, GET_THRESHOLD_SELECTOR
from app.blockchain.ownable import OWNER_FUNCTION_SELECTOR
from app.blockchain.timelock import GET_MIN_DELAY_SELECTOR
from app.core.exceptions import BlockchainRpcError
from app.models.enums import (
    AdminType,
    CentralizationLevel,
    ConfidenceLevel,
    ContractType,
    ProxyType,
    RiskLevel,
    ThreatLevel,
)
from app.schemas.scan_result import (
    ContractAnalysisData,
    LiquidityAnalysisData,
    ProtocolIntelligenceData,
    WalletIntelligenceData,
)
from app.services.contract_analyzer import ContractAnalyzer
from app.services.risk_engine import (
    REASON_ADMIN_EOA,
    REASON_NO_UPGRADE_SIGNALS,
    REASON_NOT_CONTRACT,
    REASON_PROXYADMIN_OWNER,
)

VALID_ADDRESS = "0x742d35cc6634c0532925a3b844bc9e7595f0beb0"
UNI_V3_FACTORY = "0x1f9840a85d5af5bf1d1762f925bdaddc4201f984"
PROXY_ADDRESS = "0xa231aa3388416ebc1b8f8a51b412327832524ca4"
IMPLEMENTATION_ADDRESS = "0xdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef"
ADMIN_ADDRESS = "0x1234567890123456789012345678901234567890"
PROXY_ADMIN = "0xabcdefabcdefabcdefabcdefabcdefabcdefabcd"
TIMELOCK = "0xcccccccccccccccccccccccccccccccccccccccc"


def _stable_liquidity_analyzer() -> MagicMock:
    """Return locked deep liquidity so legacy contract risk assertions stay stable."""
    mock = MagicMock()
    mock.analyze = AsyncMock(
        return_value=LiquidityAnalysisData(
            has_liquidity=True,
            liquidity_usd=Decimal("50000.00"),
            primary_dex="uniswap",
            pair_address="0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            lp_owner="0x000000000000000000000000000000000000dead",
            liquidity_locked=True,
            liquidity_lock_percentage=Decimal("100.00"),
            top_pools=[],
        )
    )
    return mock


def _stable_wallet_intelligence_analyzer() -> MagicMock:
    """Return neutral wallet intelligence so legacy contract risk assertions stay stable."""
    mock = MagicMock()
    mock.analyze = AsyncMock(return_value=WalletIntelligenceData())
    return mock


def _stable_protocol_intelligence_analyzer() -> MagicMock:
    """Return empty protocol intelligence so legacy contract risk assertions stay stable."""
    mock = MagicMock()
    mock.analyze = AsyncMock(return_value=ProtocolIntelligenceData())
    return mock


def _stable_protocol_relationship_analyzer() -> MagicMock:
    """Passthrough relationship enrichment so legacy contract risk assertions stay stable."""
    mock = MagicMock()

    def _passthrough(_address: str, *, protocol_intelligence: ProtocolIntelligenceData, **_kwargs):
        return protocol_intelligence

    mock.analyze = MagicMock(side_effect=_passthrough)
    return mock


def _stable_threat_surface_analyzer() -> MagicMock:
    """Passthrough threat surface enrichment so legacy contract risk assertions stay stable."""
    mock = MagicMock()

    def _passthrough(_address: str, *, protocol_intelligence: ProtocolIntelligenceData, **_kwargs):
        return protocol_intelligence

    mock.analyze = MagicMock(side_effect=_passthrough)
    return mock


def _make_analyzer(web3: MagicMock, **kwargs: object) -> ContractAnalyzer:
    kwargs.setdefault("liquidity_analyzer", _stable_liquidity_analyzer())
    kwargs.setdefault("wallet_intelligence_analyzer", _stable_wallet_intelligence_analyzer())
    kwargs.setdefault("protocol_intelligence_analyzer", _stable_protocol_intelligence_analyzer())
    kwargs.setdefault("protocol_relationship_analyzer", _stable_protocol_relationship_analyzer())
    kwargs.setdefault("threat_surface_analyzer", _stable_threat_surface_analyzer())
    return ContractAnalyzer(web3, **kwargs)


def _address_storage_word(address: str) -> bytes:
    return b"\x00" * 12 + bytes.fromhex(address[2:])


def _gnosis_safe_bytecode() -> bytes:
    return b"\x60\x80" + GET_OWNERS_SELECTOR + b"\x00" * 10 + GET_THRESHOLD_SELECTOR


def _owner_return_data(address: str) -> bytes:
    return b"\x00" * 12 + bytes.fromhex(address[2:])


def _min_delay_return(seconds: int) -> bytes:
    return seconds.to_bytes(32, byteorder="big")


def _normalize_call_data(data: str | bytes) -> bytes:
    if isinstance(data, bytes):
        return data
    if data.startswith("0x"):
        return bytes.fromhex(data[2:])
    return bytes.fromhex(data)


def _build_mock_web3(
    *,
    connected: bool = True,
    chain_id: int = 11155111,
    block_number: int = 12345678,
    bytecode: bytes = b"",
    storage_slots: dict[str, bytes] | None = None,
    code_by_address: dict[str, bytes] | None = None,
    owner_by_admin: dict[str, bytes] | None = None,
    min_delay_by_address: dict[str, int] | None = None,
) -> MagicMock:
    slots = storage_slots or {}
    codes = {address.lower(): code for address, code in (code_by_address or {}).items()}
    owners = {address.lower(): data for address, data in (owner_by_admin or {}).items()}
    min_delays = {address.lower(): delay for address, delay in (min_delay_by_address or {}).items()}

    class MockEth:
        async def get_code(self, address: str) -> HexBytes:
            return HexBytes(codes.get(address.lower(), bytecode))

        async def get_storage_at(self, _address: str, slot: str) -> HexBytes:
            return HexBytes(slots.get(slot, b"\x00" * 32))

        async def call(self, transaction: dict[str, str]) -> bytes:
            data = transaction.get("data", "")
            raw = _normalize_call_data(data)
            to_address = transaction["to"].lower()
            if raw[:4] == SUPPORTS_INTERFACE_SELECTOR:
                return b"\x00" * 32
            if data == OWNER_FUNCTION_SELECTOR or raw[:4] == bytes.fromhex("8da5cb5b"):
                return owners.get(to_address, b"\x00" * 32)
            if data == GET_MIN_DELAY_SELECTOR or raw[:4] == bytes.fromhex("3ecaef56"):
                if to_address in min_delays:
                    return _min_delay_return(min_delays[to_address])
                raise RuntimeError("execution reverted")
            raise RuntimeError("unexpected eth_call")

        @property
        async def chain_id(self) -> int:
            return chain_id

        @property
        async def block_number(self) -> int:
            return block_number

    web3 = MagicMock()
    web3.is_connected = AsyncMock(return_value=connected)
    web3.eth = MockEth()
    return web3


@pytest.mark.asyncio
async def test_contract_analyzer_detects_eoa() -> None:
    analyzer = ContractAnalyzer(_build_mock_web3(bytecode=b""))

    result = await analyzer.analyze(VALID_ADDRESS)

    assert result == ContractAnalysisData(
        chain_id=11155111,
        latest_block=12345678,
        is_contract=False,
        bytecode_size=0,
        is_upgradeable=False,
        implementation_address=None,
        admin_address=None,
        admin_type=None,
        owner_address=None,
        owner_type=None,
        is_timelock=False,
        min_delay=None,
        mint_capability=False,
        pause_capability=False,
        blacklist_capability=False,
        ownership_capability=False,
        trading_enabled_control=False,
        whitelist_control=False,
        blacklist_sell_blocking=False,
            transfer_tax_control=False,
            trade_simulated=False,
            can_buy=None,
            can_sell=None,
            buy_tax_bps=None,
            sell_tax_bps=None,
            risk_score=Decimal("0.00"),
        risk_level=RiskLevel.LOW,
        risk_reasons=[REASON_NOT_CONTRACT],
        contract_type=ContractType.EOA,
        proxy_type=ProxyType.NONE,
        is_verified=False,
        threat_level=ThreatLevel.LOW,
        centralization_level=CentralizationLevel.LOW,
        confidence_level=ConfidenceLevel.MEDIUM,
        governance_type=None,
        upgrade_authority=None,
        role_count=None,
        governance_roles=None,
        governance_ownership_address=None,
    )


@pytest.mark.asyncio
async def test_contract_analyzer_detects_contract_bytecode() -> None:
    bytecode = b"\x60\x80\x60\x40" + b"\x00" * 100
    analyzer = _make_analyzer(_build_mock_web3(bytecode=bytecode))

    result = await analyzer.analyze(UNI_V3_FACTORY)

    assert result.is_contract is True
    assert result.is_timelock is False
    assert result.mint_capability is False
    assert result.trading_enabled_control is False
    assert result.risk_score == Decimal("0.00")


@pytest.mark.asyncio
async def test_contract_analyzer_detects_eip1967_proxy_with_eoa_admin() -> None:
    bytecode = b"\x60\x80" + b"\x00" * 50
    storage_slots = {
        EIP1967_IMPLEMENTATION_SLOT: _address_storage_word(IMPLEMENTATION_ADDRESS),
        EIP1967_ADMIN_SLOT: _address_storage_word(ADMIN_ADDRESS),
    }
    analyzer = _make_analyzer(
        _build_mock_web3(
            bytecode=bytecode,
            storage_slots=storage_slots,
            code_by_address={ADMIN_ADDRESS: b""},
        )
    )

    result = await analyzer.analyze(PROXY_ADDRESS)

    assert result.admin_type == AdminType.EOA
    assert result.is_timelock is False
    assert result.risk_score == Decimal("100.00")


@pytest.mark.asyncio
async def test_contract_analyzer_detects_multisig_admin() -> None:
    bytecode = b"\x60\x80" + b"\x00" * 50
    storage_slots = {
        EIP1967_IMPLEMENTATION_SLOT: _address_storage_word(IMPLEMENTATION_ADDRESS),
        EIP1967_ADMIN_SLOT: _address_storage_word(ADMIN_ADDRESS),
    }
    analyzer = _make_analyzer(
        _build_mock_web3(
            bytecode=bytecode,
            storage_slots=storage_slots,
            code_by_address={ADMIN_ADDRESS: _gnosis_safe_bytecode()},
        )
    )

    result = await analyzer.analyze(PROXY_ADDRESS)

    assert result.admin_type == AdminType.MULTISIG
    assert result.risk_score == Decimal("80.00")


@pytest.mark.asyncio
async def test_contract_analyzer_traces_proxyadmin_owner() -> None:
    bytecode = b"\x60\x80" + b"\x00" * 50
    storage_slots = {
        EIP1967_IMPLEMENTATION_SLOT: _address_storage_word(IMPLEMENTATION_ADDRESS),
        EIP1967_ADMIN_SLOT: _address_storage_word(PROXY_ADMIN),
    }
    analyzer = _make_analyzer(
        _build_mock_web3(
            bytecode=bytecode,
            storage_slots=storage_slots,
            code_by_address={
                PROXY_ADMIN: b"\x60\x80\x60\x40",
                ADMIN_ADDRESS: b"",
            },
            owner_by_admin={PROXY_ADMIN: _owner_return_data(ADMIN_ADDRESS)},
        )
    )

    result = await analyzer.analyze(PROXY_ADDRESS)

    assert result.owner_address == ADMIN_ADDRESS
    assert result.owner_type == AdminType.EOA
    assert result.risk_score == Decimal("100.00")
    assert REASON_PROXYADMIN_OWNER in result.risk_reasons


@pytest.mark.asyncio
async def test_contract_analyzer_detects_timelock_governed_proxyadmin() -> None:
    bytecode = b"\x60\x80" + b"\x00" * 50
    storage_slots = {
        EIP1967_IMPLEMENTATION_SLOT: _address_storage_word(IMPLEMENTATION_ADDRESS),
        EIP1967_ADMIN_SLOT: _address_storage_word(PROXY_ADMIN),
    }
    analyzer = _make_analyzer(
        _build_mock_web3(
            bytecode=bytecode,
            storage_slots=storage_slots,
            code_by_address={
                PROXY_ADMIN: b"\x60\x80\x60\x40",
                TIMELOCK: b"\x60\x80\x60\x40",
            },
            owner_by_admin={PROXY_ADMIN: _owner_return_data(TIMELOCK)},
            min_delay_by_address={TIMELOCK: 86400},
        )
    )

    result = await analyzer.analyze(PROXY_ADDRESS)

    assert result.owner_address == TIMELOCK
    assert result.owner_type == AdminType.CONTRACT
    assert result.is_timelock is True
    assert result.min_delay == 86400
    assert result.risk_score == Decimal("77.00")
    assert "min delay 86400s" in " ".join(result.risk_reasons)


@pytest.mark.asyncio
async def test_contract_analyzer_detects_capabilities_on_implementation() -> None:
    impl_bytecode = b"\x60\x80" + next(iter(MINT_SELECTORS)) + next(iter(PAUSE_SELECTORS))
    bytecode = b"\x60\x80" + b"\x00" * 50
    storage_slots = {
        EIP1967_IMPLEMENTATION_SLOT: _address_storage_word(IMPLEMENTATION_ADDRESS),
        EIP1967_ADMIN_SLOT: _address_storage_word(ADMIN_ADDRESS),
    }
    analyzer = _make_analyzer(
        _build_mock_web3(
            bytecode=bytecode,
            storage_slots=storage_slots,
            code_by_address={
                ADMIN_ADDRESS: b"",
                IMPLEMENTATION_ADDRESS: impl_bytecode,
            },
        )
    )

    result = await analyzer.analyze(PROXY_ADDRESS)

    assert result.mint_capability is True
    assert result.pause_capability is True
    assert result.blacklist_capability is False
    assert result.risk_score == Decimal("100.00")
    assert "mint capability" in " ".join(result.risk_reasons).lower()


@pytest.mark.asyncio
async def test_contract_analyzer_detects_honeypot_on_implementation() -> None:
    impl_bytecode = (
        b"\x60\x80"
        + next(iter(TRADING_ENABLED_SELECTORS))
        + next(iter(BLACKLIST_PROBE_SELECTORS))
        + next(iter(SELL_RESTRICTION_SELECTORS))
    )
    bytecode = b"\x60\x80" + b"\x00" * 50
    storage_slots = {
        EIP1967_IMPLEMENTATION_SLOT: _address_storage_word(IMPLEMENTATION_ADDRESS),
        EIP1967_ADMIN_SLOT: _address_storage_word(ADMIN_ADDRESS),
    }
    analyzer = _make_analyzer(
        _build_mock_web3(
            bytecode=bytecode,
            storage_slots=storage_slots,
            code_by_address={
                ADMIN_ADDRESS: b"",
                IMPLEMENTATION_ADDRESS: impl_bytecode,
            },
        )
    )

    result = await analyzer.analyze(PROXY_ADDRESS)

    assert result.trading_enabled_control is True
    assert result.blacklist_sell_blocking is True
    assert result.risk_score == Decimal("100.00")
    assert "honeypot risk" in " ".join(result.risk_reasons).lower()


@pytest.mark.asyncio
async def test_contract_analyzer_raises_when_not_connected() -> None:
    analyzer = ContractAnalyzer(_build_mock_web3(connected=False))

    with pytest.raises(BlockchainRpcError, match="Unable to connect"):
        await analyzer.analyze(VALID_ADDRESS)


@pytest.mark.asyncio
async def test_contract_analyzer_raises_on_chain_id_mismatch() -> None:
    analyzer = ContractAnalyzer(_build_mock_web3(chain_id=1), expected_chain_id=11155111)

    with pytest.raises(BlockchainRpcError, match="does not match configured CHAIN_ID"):
        await analyzer.analyze(VALID_ADDRESS)
