"""ContractClassifier unit tests for known Mainnet contract profiles."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from hexbytes import HexBytes
from httpx import AsyncClient

from app.blockchain.erc165 import (
    INTERFACE_ID_ERC165,
    INTERFACE_ID_ERC721,
    SUPPORTS_INTERFACE_SELECTOR,
)
from app.blockchain.eip1967 import EIP1967_ADMIN_SLOT, EIP1967_IMPLEMENTATION_SLOT
from app.blockchain.multisig import GET_OWNERS_SELECTOR, GET_THRESHOLD_SELECTOR
from app.blockchain.timelock import GET_MIN_DELAY_SELECTOR
from app.blockchain.token_standards import (
    ERC20_APPROVE_SELECTOR,
    ERC20_BALANCE_OF_SELECTOR,
    ERC20_TOTAL_SUPPLY_SELECTOR,
    ERC20_TRANSFER_SELECTOR,
    WETH_DEPOSIT_SELECTOR,
    WETH_WITHDRAW_SELECTOR,
)
from app.models.enums import ContractType, ProxyType
from app.services.contract_classifier import ContractClassifier

USDC = "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48"
USDC_IMPLEMENTATION = "0x49616c6520310553ab54eaf32f13470da44911b2"
USDC_ADMIN = "0x8e5d455a1541782a8c085543720618f364312b04"

WETH = "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2"

GNOSIS_SAFE = "0x1234567890123456789012345678901234567890"

OZ_TIMELOCK = "0x1d9ee622962d99ea4436721a64a1666eea0baa82"


def _address_storage_word(address: str) -> bytes:
    return b"\x00" * 12 + bytes.fromhex(address[2:])


def _erc20_logic_bytecode() -> bytes:
    return (
        b"\x60\x80"
        + ERC20_TRANSFER_SELECTOR
        + ERC20_BALANCE_OF_SELECTOR
        + ERC20_TOTAL_SUPPLY_SELECTOR
        + ERC20_APPROVE_SELECTOR
    )


def _weth_bytecode() -> bytes:
    return _erc20_logic_bytecode() + WETH_DEPOSIT_SELECTOR + WETH_WITHDRAW_SELECTOR


def _safe_bytecode() -> bytes:
    return b"\x60\x80" + GET_OWNERS_SELECTOR + b"\x00" * 8 + GET_THRESHOLD_SELECTOR


def _normalize_call_data(data: str | bytes) -> bytes:
    if isinstance(data, bytes):
        return data
    if hasattr(data, "hex"):
        hex_value = data.hex()
        return bytes.fromhex(hex_value[2:] if hex_value.startswith("0x") else hex_value)
    if isinstance(data, str):
        if data.startswith("0x"):
            return bytes.fromhex(data[2:])
        return bytes.fromhex(data)
    raise TypeError(f"unsupported call data type: {type(data)!r}")


def _build_mock_web3(
    *,
    bytecode: bytes = b"",
    storage_slots: dict[str, bytes] | None = None,
    code_by_address: dict[str, bytes] | None = None,
    min_delay_by_address: dict[str, int] | None = None,
    erc165_support: dict[str, set[bytes]] | None = None,
) -> MagicMock:
    slots = storage_slots or {}
    codes = {address.lower(): code for address, code in (code_by_address or {}).items()}
    min_delays = {address.lower(): delay for address, delay in (min_delay_by_address or {}).items()}
    supported_interfaces = {
        address.lower(): interfaces for address, interfaces in (erc165_support or {}).items()
    }

    class MockEth:
        async def get_code(self, address: str) -> HexBytes:
            return HexBytes(codes.get(address.lower(), bytecode))

        async def get_storage_at(self, _address: str, slot: str) -> HexBytes:
            return HexBytes(slots.get(slot, b"\x00" * 32))

        async def call(self, transaction: dict[str, str | bytes]) -> bytes:
            raw = _normalize_call_data(transaction.get("data", b""))
            to_address = transaction["to"].lower()
            if raw[:4] == SUPPORTS_INTERFACE_SELECTOR:
                interface_id = raw[32:36]
                if interface_id in supported_interfaces.get(to_address, set()):
                    return b"\x00" * 31 + b"\x01"
                return b"\x00" * 32
            if raw[:4] == bytes.fromhex("3ecaef56"):
                if to_address in min_delays:
                    return min_delays[to_address].to_bytes(32, byteorder="big")
                raise RuntimeError("execution reverted")
            raise RuntimeError(f"unexpected eth_call data={raw.hex()}")

    web3 = MagicMock()
    web3.is_connected = AsyncMock(return_value=True)
    web3.eth = MockEth()
    return web3


class _VerifiedSourceProvider:
    async def get_verified_source(self, contract_address: str, chain_id: int) -> object:
        if contract_address.lower() in {USDC_IMPLEMENTATION.lower(), WETH.lower()}:
            return object()
        return None


@pytest.mark.asyncio
async def test_classify_usdc_proxy_as_erc20_transparent() -> None:
    classifier = ContractClassifier(
        _build_mock_web3(
            bytecode=b"\x60\x80\x60\x40",
            storage_slots={
                EIP1967_IMPLEMENTATION_SLOT: _address_storage_word(USDC_IMPLEMENTATION),
                EIP1967_ADMIN_SLOT: _address_storage_word(USDC_ADMIN),
            },
            code_by_address={USDC_IMPLEMENTATION: _erc20_logic_bytecode()},
        ),
        chain_id=1,
        source_provider=_VerifiedSourceProvider(),
    )

    result = await classifier.classify(
        USDC,
        bytecode=b"\x60\x80\x60\x40",
        is_contract=True,
        implementation_address=USDC_IMPLEMENTATION,
        implementation_bytecode=_erc20_logic_bytecode(),
        admin_address=USDC_ADMIN,
    )

    assert result.contract_type == ContractType.ERC20
    assert result.proxy_type == ProxyType.EIP1967_TRANSPARENT
    assert result.is_verified is True


@pytest.mark.asyncio
async def test_classify_weth_as_erc20() -> None:
    classifier = ContractClassifier(
        _build_mock_web3(
            bytecode=_weth_bytecode(),
            code_by_address={WETH: _weth_bytecode()},
        ),
        chain_id=1,
        source_provider=_VerifiedSourceProvider(),
    )

    result = await classifier.classify(
        WETH,
        bytecode=_weth_bytecode(),
        is_contract=True,
    )

    assert result.contract_type == ContractType.ERC20
    assert result.proxy_type == ProxyType.NONE
    assert result.is_verified is True


@pytest.mark.asyncio
async def test_classify_gnosis_safe_as_multisig() -> None:
    classifier = ContractClassifier(
        _build_mock_web3(
            bytecode=_safe_bytecode(),
            code_by_address={GNOSIS_SAFE: _safe_bytecode()},
        ),
        chain_id=1,
    )

    result = await classifier.classify(
        GNOSIS_SAFE,
        bytecode=_safe_bytecode(),
        is_contract=True,
    )

    assert result.contract_type == ContractType.MULTISIG
    assert result.proxy_type == ProxyType.NONE


@pytest.mark.asyncio
async def test_classify_openzeppelin_timelock() -> None:
    classifier = ContractClassifier(
        _build_mock_web3(
            bytecode=b"\x60\x80\x60\x40",
            min_delay_by_address={OZ_TIMELOCK.lower(): 172800},
        ),
        chain_id=1,
    )

    result = await classifier.classify(
        OZ_TIMELOCK,
        bytecode=b"\x60\x80\x60\x40",
        is_contract=True,
    )

    assert result.contract_type == ContractType.TIMELOCK
    assert result.proxy_type == ProxyType.NONE


@pytest.mark.asyncio
async def test_classify_eoa_target() -> None:
    classifier = ContractClassifier(_build_mock_web3(), chain_id=1)

    result = await classifier.classify(
        "0x742d35cc6634c0532925a3b844bc9e7595f0beb0",
        bytecode=b"",
        is_contract=False,
    )

    assert result.contract_type == ContractType.EOA
    assert result.proxy_type == ProxyType.NONE
    assert result.is_verified is False


@pytest.mark.asyncio
async def test_classify_erc721_via_erc165() -> None:
    nft = "0xbc4ca0eda7647a8ab7c2061c2e98a0250186dd9b"
    classifier = ContractClassifier(
        _build_mock_web3(
            bytecode=b"\x60\x80",
            erc165_support={
                nft.lower(): {INTERFACE_ID_ERC165, INTERFACE_ID_ERC721},
            },
        ),
        chain_id=1,
    )

    result = await classifier.classify(
        nft,
        bytecode=b"\x60\x80",
        is_contract=True,
    )

    assert result.contract_type == ContractType.ERC721


@pytest.mark.asyncio
async def test_get_scan_includes_classification_fields(client: AsyncClient) -> None:
    create_response = await client.post(
        "/api/v1/scans",
        json={"scan_type": "contract", "target_address": WETH, "chain_id": 11155111},
    )
    scan_id = create_response.json()["id"]
    response = await client.get(f"/api/v1/scans/{scan_id}")

    assert response.status_code == 200
    result = response.json()["result"]
    assert result["contract_type"] == "erc20"
    assert result["proxy_type"] == "none"
    assert result["is_verified"] is False
