"""Unit tests for runtime transaction intelligence (M9.1)."""

from __future__ import annotations

import pytest
from eth_abi import encode

from app.blockchain.contract_source_provider import ContractSourceProvider, VerifiedContractSource
from app.blockchain.risk.evidence_types import EvidenceCategory, EvidenceMetadataKey, EvidenceSeverity, EvidenceSource
from app.blockchain.runtime.transaction import (
    ApprovalKind,
    TokenStandard,
    TransactionCategory,
    TransactionFormat,
    TransactionIntelligenceEngine,
    emit_transaction_evidence,
)
from app.blockchain.runtime.transaction.models import TransactionMetadata
from app.blockchain.trade_encoding import MAX_UINT256, encode_approve, encode_transfer

SENDER = "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
RECIPIENT = "0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
TOKEN = "0xcccccccccccccccccccccccccccccccccccccccc"
SPENDER = "0xdddddddddddddddddddddddddddddddddddddddd"
PROXY = "0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee"
IMPLEMENTATION = "0x1111111111111111111111111111111111111111"
TX_HASH = "0x" + "ab" * 32


def _calldata(selector: bytes, types: list[str], values: list[object]) -> str:
    encoded = encode(types, values)
    return "0x" + selector.hex() + encoded.hex()


def _raw_tx(
    *,
    to: str | None = SENDER,
    value: int = 0,
    input_data: str = "0x",
    tx_type: int = 0,
    gas_price: int | None = 20_000_000_000,
    max_fee: int | None = None,
    max_priority: int | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "hash": TX_HASH,
        "from": SENDER,
        "to": to,
        "value": value,
        "input": input_data,
        "nonce": 1,
        "gas": 21000,
        "chainId": 1,
        "type": tx_type,
    }
    if gas_price is not None:
        payload["gasPrice"] = gas_price
    if max_fee is not None:
        payload["maxFeePerGas"] = max_fee
    if max_priority is not None:
        payload["maxPriorityFeePerGas"] = max_priority
    return payload


class MockSourceProvider(ContractSourceProvider):
    def __init__(self, abi: list[dict[str, object]] | None = None) -> None:
        self._abi = abi

    async def get_verified_source(self, contract_address: str, chain_id: int) -> VerifiedContractSource | None:
        if self._abi is None:
            return None
        return VerifiedContractSource(
            contract_name="MockToken",
            source_code="contract MockToken {}",
            abi=self._abi,
            is_proxy=False,
        )


@pytest.mark.asyncio
async def test_eth_transfer_detection() -> None:
    engine = TransactionIntelligenceEngine()
    result = await engine.analyze_transaction(
        _raw_tx(to=RECIPIENT, value=10**18, input_data="0x"),
        chain_id=1,
    )

    assert len(result.token_transfers) == 1
    assert result.token_transfers[0].standard == TokenStandard.NATIVE
    assert result.token_transfers[0].amount == 10**18
    assert result.category == TransactionCategory.TRANSFER


@pytest.mark.asyncio
async def test_erc20_transfer_detection() -> None:
    engine = TransactionIntelligenceEngine()
    result = await engine.analyze_transaction(
        _raw_tx(to=TOKEN, input_data=encode_transfer(RECIPIENT, 1_000)),
        chain_id=1,
    )

    assert result.token_transfers[0].standard == TokenStandard.ERC20
    assert result.token_transfers[0].to_address.lower() == RECIPIENT.lower()
    assert result.token_transfers[0].amount == 1_000
    assert result.decoded_function is not None
    assert result.decoded_function.function_name == "transfer"


@pytest.mark.asyncio
async def test_erc721_transfer_detection() -> None:
    engine = TransactionIntelligenceEngine()
    calldata = _calldata(bytes.fromhex("42842e0e"), ["address", "address", "uint256"], [SENDER, RECIPIENT, 42])
    result = await engine.analyze_transaction(_raw_tx(to=TOKEN, input_data=calldata), chain_id=1)

    assert result.token_transfers[0].standard == TokenStandard.ERC721
    assert result.token_transfers[0].token_id == 42


@pytest.mark.asyncio
async def test_erc1155_transfer_detection() -> None:
    engine = TransactionIntelligenceEngine()
    calldata = _calldata(
        bytes.fromhex("f242432a"),
        ["address", "address", "uint256", "uint256", "bytes"],
        [SENDER, RECIPIENT, 7, 100, b""],
    )
    result = await engine.analyze_transaction(_raw_tx(to=TOKEN, input_data=calldata), chain_id=1)

    assert result.token_transfers[0].standard == TokenStandard.ERC1155
    assert result.token_transfers[0].token_id == 7
    assert result.token_transfers[0].amount == 100


@pytest.mark.asyncio
async def test_approval_detection() -> None:
    engine = TransactionIntelligenceEngine()
    result = await engine.analyze_transaction(
        _raw_tx(to=TOKEN, input_data=encode_approve(SPENDER, 500)),
        chain_id=1,
    )

    assert len(result.approvals) == 1
    assert result.approvals[0].kind == ApprovalKind.APPROVE
    assert result.approvals[0].spender_address.lower() == SPENDER.lower()
    assert result.approvals[0].amount == 500
    assert result.category == TransactionCategory.APPROVAL


@pytest.mark.asyncio
async def test_unlimited_approval_detection() -> None:
    engine = TransactionIntelligenceEngine()
    result = await engine.analyze_transaction(
        _raw_tx(to=TOKEN, input_data=encode_approve(SPENDER, MAX_UINT256)),
        chain_id=1,
    )

    assert result.approvals[0].is_unlimited is True
    assert result.approvals[0].is_infinite_allowance is True
    signals = {item.metadata.get(EvidenceMetadataKey.SIGNAL.value) for item in result.risk_evidence}
    assert "unlimited_approval" in signals


@pytest.mark.asyncio
async def test_upgrade_transaction_detection() -> None:
    engine = TransactionIntelligenceEngine()
    calldata = _calldata(bytes.fromhex("3659cfe6"), ["address"], [IMPLEMENTATION])
    result = await engine.analyze_transaction(_raw_tx(to=PROXY, input_data=calldata), chain_id=1)

    assert result.category == TransactionCategory.UPGRADE
    assert result.privileged_actions[0].operation.value == "upgradeTo"
    signals = {item.metadata.get(EvidenceMetadataKey.SIGNAL.value) for item in result.risk_evidence}
    assert "upgrade_executed" in signals


@pytest.mark.asyncio
async def test_mint_transaction_detection() -> None:
    engine = TransactionIntelligenceEngine()
    calldata = _calldata(bytes.fromhex("40c10f19"), ["address", "uint256"], [RECIPIENT, 10**24])
    result = await engine.analyze_transaction(_raw_tx(to=TOKEN, input_data=calldata), chain_id=1)

    assert result.category == TransactionCategory.MINT
    assert result.privileged_actions[0].operation.value == "mint"
    assert result.privileged_actions[0].is_large_transfer is True


@pytest.mark.asyncio
async def test_governance_transaction_detection() -> None:
    engine = TransactionIntelligenceEngine()
    calldata = _calldata(bytes.fromhex("56781388"), ["uint256", "uint8"], [1, 1])
    result = await engine.analyze_transaction(_raw_tx(to=PROXY, input_data=calldata), chain_id=1)

    assert result.category == TransactionCategory.GOVERNANCE
    assert result.decoded_function is not None
    assert result.decoded_function.function_name == "castVote"


@pytest.mark.asyncio
async def test_selector_fallback_decoding() -> None:
    engine = TransactionIntelligenceEngine(source_provider=MockSourceProvider(abi=None))
    result = await engine.analyze_transaction(
        _raw_tx(to=TOKEN, input_data=encode_transfer(RECIPIENT, 123)),
        chain_id=1,
    )

    assert result.decoded_function is not None
    assert result.decoded_function.decode_source == "selector_registry"
    assert result.decoded_function.function_name == "transfer"


@pytest.mark.asyncio
async def test_verified_abi_decoding() -> None:
    abi = [
        {
            "type": "function",
            "name": "transfer",
            "inputs": [
                {"name": "recipient", "type": "address"},
                {"name": "amount", "type": "uint256"},
            ],
            "outputs": [{"name": "", "type": "bool"}],
        }
    ]
    engine = TransactionIntelligenceEngine(source_provider=MockSourceProvider(abi=abi))
    result = await engine.analyze_transaction(
        _raw_tx(to=TOKEN, input_data=encode_transfer(RECIPIENT, 999)),
        chain_id=1,
    )

    assert result.decoded_function is not None
    assert result.decoded_function.decode_source == "verified_abi"
    assert result.decoded_function.arguments[0].name == "recipient"


@pytest.mark.asyncio
async def test_legacy_and_eip1559_and_deployment_formats() -> None:
    engine = TransactionIntelligenceEngine()

    legacy = await engine.analyze_transaction(_raw_tx(to=RECIPIENT, value=1, tx_type=0), chain_id=1)
    assert legacy.metadata.transaction_format == TransactionFormat.LEGACY

    eip1559 = await engine.analyze_transaction(
        _raw_tx(
            to=RECIPIENT,
            value=1,
            tx_type=2,
            gas_price=None,
            max_fee=30_000_000_000,
            max_priority=2_000_000_000,
        ),
        chain_id=1,
    )
    assert eip1559.metadata.transaction_format == TransactionFormat.EIP1559

    deployment = await engine.analyze_transaction(_raw_tx(to=None, value=0, input_data="0x60806040"), chain_id=1)
    assert deployment.metadata.transaction_format == TransactionFormat.CONTRACT_CREATION
    assert deployment.category == TransactionCategory.DEPLOYMENT


def test_evidence_generation_does_not_assign_transaction_risk_score() -> None:
    metadata = TransactionMetadata(
        transaction_hash=TX_HASH,
        chain_id=1,
        from_address=SENDER,
        to_address=TOKEN,
        value_wei=0,
        nonce=1,
        gas=100000,
        gas_price_wei=1,
        max_fee_per_gas_wei=None,
        max_priority_fee_per_gas_wei=None,
        transaction_format=TransactionFormat.LEGACY,
    )
    from app.blockchain.runtime.transaction.models import ApprovalFinding

    approval = ApprovalFinding(
        kind=ApprovalKind.APPROVE,
        token_address=TOKEN,
        owner_address=SENDER,
        spender_address=SPENDER,
        amount=MAX_UINT256,
        is_unlimited=True,
        is_infinite_allowance=True,
    )
    evidence = emit_transaction_evidence(
        metadata=metadata,
        category=TransactionCategory.APPROVAL,
        approvals=(approval,),
        privileged_actions=(),
        decoded_function=None,
    )

    assert evidence
    assert all(item.score == 0 for item in evidence)
    assert all(item.metadata.get(EvidenceMetadataKey.REASON_ONLY.value) for item in evidence)
    assert any(item.source == EvidenceSource.CAPABILITY for item in evidence)
    assert any(item.category == EvidenceCategory.AUTHORITY for item in evidence)
    assert any(item.severity == EvidenceSeverity.HIGH for item in evidence)
