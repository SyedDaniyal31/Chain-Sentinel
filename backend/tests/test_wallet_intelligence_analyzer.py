"""WalletIntelligenceAnalyzer unit tests (M5.2)."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.blockchain.wallet.reputation_provider import WalletReputationResult
from app.blockchain.wallet.wallet_history_provider import ExplorerTransaction
from app.models.enums import ConfidenceLevel, FundingSourceType
from app.services.wallet_intelligence_analyzer import WalletIntelligenceAnalyzer


class _FakeHistory:
    async def get_contract_creation(self, contract_address: str, chain_id: int):
        return ExplorerTransaction(
            hash="0xdeploy",
            from_address="0x1111111111111111111111111111111111111111",
            to_address=None,
            value_wei=0,
            block_number=100,
            timestamp=1_700_000_000,
        )

    async def get_wallet_transactions(self, wallet_address: str, chain_id: int, *, limit: int = 25):
        return [
            ExplorerTransaction(
                hash="0xfund",
                from_address="0xd90e2f925ba723939877147291111569bc6c9620",
                to_address=wallet_address.lower(),
                value_wei=10**18,
                block_number=50,
                timestamp=1_699_000_000,
            )
        ]


class _FakeReputation:
    async def lookup(self, wallet_address: str, chain_id: int) -> WalletReputationResult:
        return WalletReputationResult(
            sanctioned=True,
            known_scam=True,
            confidence=ConfidenceLevel.HIGH,
        )


@pytest.mark.asyncio
async def test_wallet_intelligence_analyzer_builds_full_payload() -> None:
    analyzer = WalletIntelligenceAnalyzer(
        chain_id=1,
        history_provider=_FakeHistory(),
        reputation_provider=_FakeReputation(),
    )

    result = await analyzer.analyze(
        "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        governance_ownership_address="0x2222222222222222222222222222222222222222",
        lp_owner="0x1111111111111111111111111111111111111111",
    )

    assert result.ownership.deployer == "0x1111111111111111111111111111111111111111"
    assert result.funding.funding_source == FundingSourceType.TORNADO
    assert result.tornado_funded_deployer is True
    assert result.reputation.sanctioned is True
    assert result.wallet_risk_score > 0
    assert result.graph.edges


@pytest.mark.asyncio
async def test_wallet_intelligence_analyzer_empty_without_history_provider() -> None:
    analyzer = WalletIntelligenceAnalyzer(chain_id=1, history_provider=None)

    result = await analyzer.analyze("0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")

    assert result.wallet_risk_score == 0
    assert result.ownership.deployer is None
