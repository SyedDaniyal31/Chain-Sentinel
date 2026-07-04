"""Wallet intelligence builder unit tests (M5.2)."""

from app.blockchain.wallet.funding_classifier import classify_funding_source, is_fresh_wallet
from app.blockchain.wallet.reputation_provider import WalletReputationResult
from app.blockchain.wallet.wallet_history_provider import ExplorerTransaction
from app.blockchain.wallet.wallet_intelligence import (
    WalletAnalysisContext,
    build_wallet_intelligence,
    compute_wallet_risk_score,
)
from app.models.enums import AdminType, FundingSourceType, UpgradeAuthority


def _tx(
    *,
    from_address: str,
    to_address: str | None = None,
    value_wei: int = 1,
    block_number: int = 1,
    timestamp: int = 1_700_000_000,
) -> ExplorerTransaction:
    return ExplorerTransaction(
        hash="0xabc",
        from_address=from_address.lower(),
        to_address=to_address.lower() if to_address else None,
        value_wei=value_wei,
        block_number=block_number,
        timestamp=timestamp,
    )


def test_classify_funding_source_exchange() -> None:
    assert (
        classify_funding_source("0x28c6c06298d014dbb8898931c1fbd413e3765460")
        == FundingSourceType.EXCHANGE
    )


def test_classify_funding_source_tornado() -> None:
    assert (
        classify_funding_source("0xd90e2f925ba723939877147291111569bc6c9620")
        == FundingSourceType.TORNADO
    )


def test_is_fresh_wallet_with_few_transactions() -> None:
    deployer = "0x1111111111111111111111111111111111111111"
    txs = [_tx(from_address="0x2222222222222222222222222222222222222222", to_address=deployer)]
    assert is_fresh_wallet(txs) is True


def test_build_wallet_intelligence_detects_creator_lp_overlap() -> None:
    creator = "0x1111111111111111111111111111111111111111"
    contract = "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    context = WalletAnalysisContext(
        chain_id=1,
        contract_address=contract,
        admin_address=None,
        admin_type=None,
        owner_address=creator,
        owner_type=AdminType.EOA,
        governance_ownership_address=creator,
        is_timelock=False,
        upgrade_authority=UpgradeAuthority.EOA,
        lp_owner=creator,
    )
    creation_tx = _tx(from_address=creator, to_address=None)
    deployer_txs = [
        _tx(
            from_address="0x28c6c06298d014dbb8898931c1fbd413e3765460",
            to_address=creator,
            block_number=10,
        )
    ]

    result = build_wallet_intelligence(
        context,
        creation_tx=creation_tx,
        deployer_transactions=deployer_txs,
        reputation_result=WalletReputationResult(),
    )

    assert result.ownership.creator == creator
    assert result.lp_owner_is_creator is True
    assert result.creator_owns_majority is True
    assert result.exchange_funded_deployer is True
    assert result.funding.funding_source == FundingSourceType.EXCHANGE
    assert len(result.graph.nodes) >= 2


def test_compute_wallet_risk_score_tornado_funding() -> None:
    signals = {
        "deployer_is_fresh": True,
        "creator_owns_majority": False,
        "lp_owner_is_creator": False,
        "exchange_funded_deployer": False,
        "tornado_funded_deployer": True,
        "treasury_is_multisig": False,
        "wallet_known_scam": False,
    }
    score = compute_wallet_risk_score(signals)
    assert score == 47
