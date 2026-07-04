"""M3 capability intelligence unit tests."""

from app.blockchain.capability_catalog import CAPABILITY_KEYS, CAPABILITY_CATALOG
from app.blockchain.capability_intelligence import (
    build_capability_inventory,
    enabled_capability_count,
    legacy_flags_from_inventory,
)
from app.blockchain.capability import MINT_SELECTORS, PAUSE_SELECTORS
from app.models.enums import CapabilityDetectionMethod, CapabilitySeverity
from app.schemas.scan_result import GovernanceRoleData


def test_catalog_covers_all_required_capabilities() -> None:
    required = {
        "mint",
        "burn",
        "pause",
        "blacklist",
        "whitelist",
        "freeze",
        "seize",
        "trading_gate",
        "max_wallet",
        "max_transaction",
        "cooldown",
        "anti_bot",
        "buy_tax",
        "sell_tax",
        "dynamic_tax",
        "treasury_fee",
        "fee_exemption",
        "transfer_ownership",
        "renounce_ownership",
        "grant_role",
        "revoke_role",
    }
    assert required == CAPABILITY_KEYS
    assert len(CAPABILITY_CATALOG) == len(required)


def test_build_inventory_detects_bytecode_mint_and_pause() -> None:
    bytecode = b"\x60\x80" + next(iter(MINT_SELECTORS)) + next(iter(PAUSE_SELECTORS))
    inventory = build_capability_inventory(logic_bytecode=bytecode)

    assert inventory["mint"].enabled is True
    assert inventory["pause"].enabled is True
    assert inventory["mint"].detection_method == CapabilityDetectionMethod.BYTECODE
    assert inventory["mint"].severity == CapabilitySeverity.CRITICAL
    assert enabled_capability_count(inventory) >= 2


def test_build_inventory_maps_minter_role_to_controller() -> None:
    inventory = build_capability_inventory(
        logic_bytecode=b"\x60\x80",
        governance_roles=[
            GovernanceRoleData(
                name="MINTER_ROLE",
                role_id="0x" + "ab" * 32,
                admin_role_name="DEFAULT_ADMIN_ROLE",
                admin_role_id="0x" + "00" * 32,
            )
        ],
    )

    assert inventory["mint"].enabled is True
    assert inventory["mint"].controller == "MINTER_ROLE"
    assert inventory["mint"].detection_method == CapabilityDetectionMethod.ROLE


def test_build_inventory_simulation_enriches_sell_tax() -> None:
    inventory = build_capability_inventory(
        logic_bytecode=b"\x60\x80",
        trade_simulated=True,
        sell_tax_bps=9900,
    )

    assert inventory["sell_tax"].enabled is True
    assert inventory["sell_tax"].detection_method == CapabilityDetectionMethod.SIMULATION


def test_legacy_flags_from_inventory() -> None:
    inventory = build_capability_inventory(
        logic_bytecode=b"\x60\x80" + next(iter(MINT_SELECTORS)) + bytes.fromhex("715018a6")
    )
    mint, pause, blacklist, ownership = legacy_flags_from_inventory(inventory)

    assert mint is True
    assert pause is False
    assert ownership is True
