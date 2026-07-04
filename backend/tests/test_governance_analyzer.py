"""GovernanceAnalyzer unit tests."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from hexbytes import HexBytes

from app.blockchain.access_control import (
    BURNER_ROLE,
    DEFAULT_ADMIN_ROLE,
    GET_ROLE_ADMIN_SELECTOR,
    HAS_ROLE_SELECTOR,
    MINTER_ROLE,
    PAUSER_ROLE,
    UPGRADER_ROLE,
)
from app.blockchain.eip1967 import EIP1967_ADMIN_SLOT, EIP1967_IMPLEMENTATION_SLOT
from app.blockchain.governance_patterns import PENDING_OWNER_SELECTOR
from app.blockchain.multisig import GET_OWNERS_SELECTOR, GET_THRESHOLD_SELECTOR
from app.blockchain.ownable import OWNER_FUNCTION_SELECTOR
from app.blockchain.timelock import GET_MIN_DELAY_SELECTOR
from app.models.enums import AdminType, ContractType, GovernanceType, UpgradeAuthority
from app.services.governance_analyzer import GovernanceAnalyzer

IMPLEMENTATION = "0xdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef"
ADMIN = "0x1234567890123456789012345678901234567890"
PROXY_ADMIN = "0xabcdefabcdefabcdefabcdefabcdefabcdefabcd"
OWNER = "0x742d35cc6634c0532925a3b844bc9e7595f0beb0"
TIMELOCK = "0xcccccccccccccccccccccccccccccccccccccccc"


def _address_storage_word(address: str) -> bytes:
    return b"\x00" * 12 + bytes.fromhex(address[2:])


def _normalize_call_data(data: str | bytes) -> bytes:
    if isinstance(data, bytes):
        return data
    if data.startswith("0x"):
        return bytes.fromhex(data[2:])
    return bytes.fromhex(data)


def _build_mock_web3(
    *,
    bytecode: bytes = b"",
    storage_slots: dict[str, bytes] | None = None,
    role_admins: dict[bytes, bytes] | None = None,
    owner_by_address: dict[str, bytes] | None = None,
    min_delay_by_address: dict[str, int] | None = None,
) -> MagicMock:
    slots = storage_slots or {}
    admins = dict(role_admins or {})
    owners = {address.lower(): data for address, data in (owner_by_address or {}).items()}
    min_delays = {address.lower(): delay for address, delay in (min_delay_by_address or {}).items()}

    class MockEth:
        async def get_code(self, _address: str) -> HexBytes:
            return HexBytes(bytecode)

        async def get_storage_at(self, _address: str, slot: str) -> HexBytes:
            return HexBytes(slots.get(slot, b"\x00" * 32))

        async def call(self, transaction: dict[str, str | bytes]) -> bytes:
            raw = _normalize_call_data(transaction.get("data", b""))
            to_address = transaction["to"].lower()
            if raw[:4] == GET_ROLE_ADMIN_SELECTOR:
                role_id = raw[4:36]
                if role_id in admins:
                    return admins[role_id].rjust(32, b"\x00")
                raise RuntimeError("execution reverted")
            if raw == OWNER_FUNCTION_SELECTOR or raw[:4] == bytes.fromhex("8da5cb5b"):
                return owners.get(to_address, b"\x00" * 32)
            if raw[:4] == bytes.fromhex("3ecaef56"):
                if to_address in min_delays:
                    return min_delays[to_address].to_bytes(32, byteorder="big")
                raise RuntimeError("execution reverted")
            raise RuntimeError(f"unexpected eth_call data={raw.hex()}")

    web3 = MagicMock()
    web3.is_connected = AsyncMock(return_value=True)
    web3.eth = MockEth()
    return web3


def _access_control_bytecode() -> bytes:
    return b"\x60\x80" + GET_ROLE_ADMIN_SELECTOR + HAS_ROLE_SELECTOR


def _access_control_role_admins() -> dict[bytes, bytes]:
    return {
        DEFAULT_ADMIN_ROLE: DEFAULT_ADMIN_ROLE,
        MINTER_ROLE: DEFAULT_ADMIN_ROLE,
        PAUSER_ROLE: DEFAULT_ADMIN_ROLE,
        UPGRADER_ROLE: DEFAULT_ADMIN_ROLE,
        BURNER_ROLE: DEFAULT_ADMIN_ROLE,
    }


@pytest.mark.asyncio
async def test_governance_detects_access_control_roles_and_hierarchy() -> None:
    logic = _access_control_bytecode()
    analyzer = GovernanceAnalyzer(
        _build_mock_web3(
            bytecode=logic,
            role_admins=_access_control_role_admins(),
            owner_by_address={IMPLEMENTATION.lower(): _address_storage_word(OWNER)},
        )
    )

    result = await analyzer.analyze(
        "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48",
        bytecode=logic,
        logic_address=IMPLEMENTATION,
        logic_bytecode=logic,
        is_upgradeable=False,
        admin_address=None,
        admin_type=None,
        owner_address=None,
        owner_type=None,
        is_timelock=False,
        ownership_capability=True,
        contract_type=ContractType.ERC20,
    )

    assert result.governance_type == GovernanceType.ACCESS_CONTROL
    assert result.role_count == 5
    assert result.roles[0].name == "DEFAULT_ADMIN_ROLE"
    assert result.roles[1].admin_role_name == "DEFAULT_ADMIN_ROLE"
    assert result.ownership_address == OWNER.lower()


@pytest.mark.asyncio
async def test_governance_detects_timelock_upgrade_authority() -> None:
    analyzer = GovernanceAnalyzer(
        _build_mock_web3(
            bytecode=b"\x60\x80",
            storage_slots={
                EIP1967_IMPLEMENTATION_SLOT: _address_storage_word(IMPLEMENTATION),
                EIP1967_ADMIN_SLOT: _address_storage_word(PROXY_ADMIN),
            },
            min_delay_by_address={PROXY_ADMIN.lower(): 86400},
            owner_by_address={PROXY_ADMIN.lower(): _address_storage_word(TIMELOCK)},
        )
    )

    result = await analyzer.analyze(
        "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48",
        bytecode=b"\x60\x80",
        logic_address=IMPLEMENTATION,
        logic_bytecode=b"\x60\x80",
        is_upgradeable=True,
        admin_address=PROXY_ADMIN,
        admin_type=AdminType.CONTRACT,
        owner_address=TIMELOCK,
        owner_type=AdminType.CONTRACT,
        is_timelock=True,
        ownership_capability=False,
        contract_type=ContractType.PROXY,
    )

    assert result.governance_type == GovernanceType.TIMELOCK
    assert result.upgrade_authority == UpgradeAuthority.TIMELOCK
    assert result.has_timelock is True


@pytest.mark.asyncio
async def test_governance_detects_eoa_upgrade_authority() -> None:
    analyzer = GovernanceAnalyzer(_build_mock_web3(bytecode=b"\x60\x80"))

    result = await analyzer.analyze(
        "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48",
        bytecode=b"\x60\x80",
        logic_address=IMPLEMENTATION,
        logic_bytecode=b"\x60\x80",
        is_upgradeable=True,
        admin_address=ADMIN,
        admin_type=AdminType.EOA,
        owner_address=None,
        owner_type=None,
        is_timelock=False,
        ownership_capability=False,
        contract_type=ContractType.PROXY,
    )

    assert result.upgrade_authority == UpgradeAuthority.EOA
    assert result.governance_type in {GovernanceType.PROXY_ADMIN, GovernanceType.UNKNOWN}


@pytest.mark.asyncio
async def test_governance_detects_multisig_pattern() -> None:
    safe_bytecode = b"\x60\x80" + GET_OWNERS_SELECTOR + GET_THRESHOLD_SELECTOR
    analyzer = GovernanceAnalyzer(_build_mock_web3(bytecode=safe_bytecode))

    result = await analyzer.analyze(
        ADMIN,
        bytecode=safe_bytecode,
        logic_address=ADMIN,
        logic_bytecode=safe_bytecode,
        is_upgradeable=False,
        admin_address=None,
        admin_type=None,
        owner_address=None,
        owner_type=None,
        is_timelock=False,
        ownership_capability=False,
        contract_type=ContractType.MULTISIG,
    )

    assert result.governance_type == GovernanceType.MULTISIG


@pytest.mark.asyncio
async def test_governance_detects_ownable2step_pattern() -> None:
    logic = b"\x60\x80" + PENDING_OWNER_SELECTOR + bytes.fromhex(OWNER_FUNCTION_SELECTOR[2:])
    analyzer = GovernanceAnalyzer(
        _build_mock_web3(
            bytecode=logic,
            owner_by_address={"0x1111111111111111111111111111111111111111": _address_storage_word(OWNER)},
        )
    )

    result = await analyzer.analyze(
        "0x1111111111111111111111111111111111111111",
        bytecode=logic,
        logic_address="0x1111111111111111111111111111111111111111",
        logic_bytecode=logic,
        is_upgradeable=False,
        admin_address=None,
        admin_type=None,
        owner_address=None,
        owner_type=None,
        is_timelock=False,
        ownership_capability=True,
        contract_type=ContractType.UNKNOWN,
    )

    assert result.governance_type == GovernanceType.OWNABLE2STEP


@pytest.mark.asyncio
async def test_governance_reads_minter_role_admin() -> None:
    logic = _access_control_bytecode()
    analyzer = GovernanceAnalyzer(
        _build_mock_web3(
            bytecode=logic,
            role_admins={MINTER_ROLE: DEFAULT_ADMIN_ROLE},
        )
    )

    result = await analyzer.analyze(
        IMPLEMENTATION,
        bytecode=logic,
        logic_address=IMPLEMENTATION,
        logic_bytecode=logic,
        is_upgradeable=False,
        admin_address=None,
        admin_type=None,
        owner_address=None,
        owner_type=None,
        is_timelock=False,
        ownership_capability=False,
        contract_type=ContractType.ERC20,
    )

    assert result.role_count == 1
    assert result.roles[0].name == "MINTER_ROLE"
    assert result.roles[0].admin_role_name == "DEFAULT_ADMIN_ROLE"


@pytest.mark.asyncio
async def test_get_scan_includes_governance_object(client) -> None:
    create_response = await client.post(
        "/api/v1/scans",
        json={"scan_type": "contract", "target_address": "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2", "chain_id": 11155111},
    )
    scan_id = create_response.json()["id"]
    response = await client.get(f"/api/v1/scans/{scan_id}")

    assert response.status_code == 200
    result = response.json()["result"]
    assert "governance" in result
    governance = result["governance"]
    assert governance["governance_type"] == "ownable"
    assert governance["upgrade_authority"] == "none"
    assert governance["has_timelock"] is False
    assert governance["role_count"] == 0
    assert governance["roles"] == []
    assert result["governance_type"] == "ownable"
