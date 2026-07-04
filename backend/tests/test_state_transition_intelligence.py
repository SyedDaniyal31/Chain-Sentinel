"""Unit tests for runtime state transition intelligence (M9.3)."""

from __future__ import annotations

import pytest

from app.blockchain.eip1967 import EIP1967_ADMIN_SLOT, EIP1967_IMPLEMENTATION_SLOT
from app.blockchain.risk.evidence_types import EvidenceMetadataKey, EvidenceSeverity, EvidenceSource
from app.blockchain.runtime.state import (
    AllowanceChangeKind,
    BalanceAssetType,
    OwnershipRole,
    RawAllowanceDiff,
    RawBalanceDiff,
    RawStateLog,
    RawStateTransition,
    RawStorageDiff,
    RawSupplyDiff,
    StateTransitionEngine,
    StaticStateTransitionProvider,
    StorageSlotKind,
    SupplyChangeKind,
    emit_state_evidence,
)
from app.blockchain.runtime.state.event_state_mapper import (
    TOPIC_APPROVAL,
    TOPIC_OWNERSHIP_TRANSFERRED,
    TOPIC_TRANSFER,
)
from app.blockchain.runtime.state.state_diff_builder import StateDiffBuilder

SENDER = "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
RECIPIENT = "0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
PROXY = "0xcccccccccccccccccccccccccccccccccccccccc"
IMPLEMENTATION = "0xdddddddddddddddddddddddddddddddddddddddd"
NEW_IMPLEMENTATION = "0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee"
ADMIN = "0x1111111111111111111111111111111111111111"
NEW_ADMIN = "0x2222222222222222222222222222222222222222"
TOKEN = "0x3333333333333333333333333333333333333333"
SPENDER = "0x4444444444444444444444444444444444444444"
TX_HASH = "0x" + "ef" * 32
MAX_UINT256 = (1 << 256) - 1


def _word_address(address: str) -> str:
    return "0x" + address.lower().removeprefix("0x").rjust(64, "0")


def _topic_address(address: str) -> str:
    return _word_address(address)


def _uint_word(value: int) -> str:
    return "0x" + format(value, "064x")


def _transition(**overrides: object) -> RawStateTransition:
    payload = {
        "transaction_hash": TX_HASH,
        "block_number": 100,
        "storage_diffs": (),
        "balance_diffs": (),
        "allowance_diffs": (),
        "supply_diffs": (),
        "logs": (),
        "provider_name": "test",
        "chain_id": 1,
    }
    payload.update(overrides)
    return RawStateTransition(**payload)


@pytest.mark.asyncio
async def test_implementation_slot_update() -> None:
    transition = _transition(
        storage_diffs=(
            RawStorageDiff(
                contract_address=PROXY,
                slot=EIP1967_IMPLEMENTATION_SLOT,
                before=_word_address(IMPLEMENTATION),
                after=_word_address(NEW_IMPLEMENTATION),
            ),
        )
    )
    report = await StateTransitionEngine().analyze_transition(transition)

    assert len(report.storage_changes) == 1
    assert report.storage_changes[0].slot_kind == StorageSlotKind.IMPLEMENTATION
    signals = {item.metadata.get(EvidenceMetadataKey.SIGNAL.value) for item in report.risk_evidence}
    assert "implementation_changed" in signals


@pytest.mark.asyncio
async def test_owner_transfer_from_storage_and_event() -> None:
    transition = _transition(
        storage_diffs=(
            RawStorageDiff(
                contract_address=TOKEN,
                slot="0x0000000000000000000000000000000000000000000000000000000000000000",
                before=_word_address(SENDER),
                after=_word_address(RECIPIENT),
            ),
        ),
        logs=(
            RawStateLog(
                contract_address=TOKEN,
                topics=(
                    TOPIC_OWNERSHIP_TRANSFERRED,
                    _topic_address(SENDER),
                    _topic_address(RECIPIENT),
                ),
                data=b"",
            ),
        ),
    )
    report = await StateTransitionEngine().analyze_transition(transition)

    assert any(change.role == OwnershipRole.OWNER for change in report.ownership_changes)
    assert any(item.metadata.get("signal") == "owner_changed" or item.metadata.get(EvidenceMetadataKey.SIGNAL.value) == "owner_changed" for item in report.risk_evidence)


@pytest.mark.asyncio
async def test_proxy_admin_change() -> None:
    transition = _transition(
        storage_diffs=(
            RawStorageDiff(
                contract_address=PROXY,
                slot=EIP1967_ADMIN_SLOT,
                before=_word_address(ADMIN),
                after=_word_address(NEW_ADMIN),
            ),
        )
    )
    report = await StateTransitionEngine().analyze_transition(transition)

    assert any(change.role == OwnershipRole.PROXY_ADMIN for change in report.ownership_changes)
    assert report.storage_changes[0].slot_kind == StorageSlotKind.PROXY_ADMIN


@pytest.mark.asyncio
async def test_erc20_balance_update() -> None:
    transition = _transition(
        balance_diffs=(
            RawBalanceDiff(
                asset_type=BalanceAssetType.ERC20,
                contract_address=TOKEN,
                account_address=RECIPIENT,
                before=0,
                after=1_000_000,
            ),
        ),
        logs=(
            RawStateLog(
                contract_address=TOKEN,
                topics=(TOPIC_TRANSFER, _topic_address(SENDER), _topic_address(RECIPIENT)),
                data=bytes.fromhex(_uint_word(1_000_000)[2:]),
            ),
        ),
    )
    report = await StateTransitionEngine().analyze_transition(transition)

    assert any(change.asset_type == BalanceAssetType.ERC20 for change in report.balance_changes)
    assert report.balance_changes[0].delta == 1_000_000


@pytest.mark.asyncio
async def test_erc721_transfer_from_log() -> None:
    token_id = 42
    transition = _transition(
        logs=(
            RawStateLog(
                contract_address=TOKEN,
                topics=(
                    TOPIC_TRANSFER,
                    _topic_address(SENDER),
                    _topic_address(RECIPIENT),
                    _uint_word(token_id),
                ),
                data=b"",
            ),
        )
    )
    report = await StateTransitionEngine().analyze_transition(transition)

    assert any(change.asset_type == BalanceAssetType.ERC721 for change in report.balance_changes)
    assert any(event.event_kind.value == "transfer" for event in report.mapped_state_events)


@pytest.mark.asyncio
async def test_erc1155_balance_update() -> None:
    transition = _transition(
        balance_diffs=(
            RawBalanceDiff(
                asset_type=BalanceAssetType.ERC1155,
                contract_address=TOKEN,
                account_address=RECIPIENT,
                before=0,
                after=5,
                token_id=7,
            ),
        )
    )
    report = await StateTransitionEngine().analyze_transition(transition)

    assert report.balance_changes[0].asset_type == BalanceAssetType.ERC1155
    assert report.balance_changes[0].token_id == 7


@pytest.mark.asyncio
async def test_unlimited_approval() -> None:
    transition = _transition(
        allowance_diffs=(
            RawAllowanceDiff(
                token_address=TOKEN,
                owner_address=SENDER,
                spender_address=SPENDER,
                before=0,
                after=MAX_UINT256,
            ),
        ),
        logs=(
            RawStateLog(
                contract_address=TOKEN,
                topics=(TOPIC_APPROVAL, _topic_address(SENDER), _topic_address(SPENDER)),
                data=bytes.fromhex(_uint_word(MAX_UINT256)[2:]),
            ),
        ),
    )
    report = await StateTransitionEngine().analyze_transition(transition)

    assert any(change.is_unlimited for change in report.allowance_changes)
    assert any(
        item.metadata.get(EvidenceMetadataKey.SIGNAL.value) == "unlimited_allowance_granted"
        for item in report.risk_evidence
    )


@pytest.mark.asyncio
async def test_mint_and_burn_supply_changes() -> None:
    transition = _transition(
        supply_diffs=(
            RawSupplyDiff(token_address=TOKEN, before=1_000, after=1_500),
            RawSupplyDiff(token_address=TOKEN, before=1_500, after=1_200),
        )
    )
    report = await StateTransitionEngine().analyze_transition(transition)

    kinds = {change.kind for change in report.supply_changes}
    assert SupplyChangeKind.MINT in kinds
    assert SupplyChangeKind.BURN in kinds


@pytest.mark.asyncio
async def test_large_supply_inflation_evidence() -> None:
    transition = _transition(
        supply_diffs=(
            RawSupplyDiff(token_address=TOKEN, before=0, after=10**25),
        )
    )
    report = await StateTransitionEngine().analyze_transition(transition)

    assert report.supply_changes[0].kind == SupplyChangeKind.INFLATION
    assert any(
        item.metadata.get(EvidenceMetadataKey.SIGNAL.value) == "large_supply_inflation"
        for item in report.risk_evidence
    )


def test_evidence_generation_does_not_compute_state_risk_score() -> None:
    bundle = StateDiffBuilder().build(
        _transition(
            allowance_diffs=(
                RawAllowanceDiff(
                    token_address=TOKEN,
                    owner_address=SENDER,
                    spender_address=SPENDER,
                    before=0,
                    after=MAX_UINT256,
                ),
            )
        )
    )
    evidence = emit_state_evidence(transaction_hash=TX_HASH, bundle=bundle)

    assert evidence
    assert all(item.score == 0 for item in evidence)
    assert all(item.metadata.get(EvidenceMetadataKey.REASON_ONLY.value) for item in evidence)
    assert any(item.source == EvidenceSource.CAPABILITY for item in evidence)
    assert any(item.severity == EvidenceSeverity.HIGH for item in evidence)


@pytest.mark.asyncio
async def test_deterministic_state_diff_ordering() -> None:
    transition = _transition(
        storage_diffs=(
            RawStorageDiff(PROXY, EIP1967_ADMIN_SLOT, _word_address(ADMIN), _word_address(NEW_ADMIN)),
            RawStorageDiff(PROXY, EIP1967_IMPLEMENTATION_SLOT, _word_address(IMPLEMENTATION), _word_address(NEW_IMPLEMENTATION)),
        ),
        supply_diffs=(RawSupplyDiff(TOKEN, 100, 200),),
    )
    report_one = await StateTransitionEngine().analyze_transition(transition)
    report_two = await StateTransitionEngine().analyze_transition(transition)

    assert [item.slot for item in report_one.storage_changes] == [
        item.slot for item in report_two.storage_changes
    ]
    assert [item.kind for item in report_one.supply_changes] == [
        item.kind for item in report_two.supply_changes
    ]
    assert [item.id for item in report_one.risk_evidence] == [item.id for item in report_two.risk_evidence]


@pytest.mark.asyncio
async def test_hash_analysis_via_static_provider() -> None:
    transition = _transition(
        balance_diffs=(
            RawBalanceDiff(
                asset_type=BalanceAssetType.NATIVE,
                contract_address=None,
                account_address=RECIPIENT,
                before=0,
                after=10**18,
            ),
        )
    )
    provider = StaticStateTransitionProvider({TX_HASH: transition})
    report = await StateTransitionEngine(state_provider=provider).analyze_hash(TX_HASH, chain_id=1)

    assert report.transaction_hash == TX_HASH
    assert report.provider_name == "static"
