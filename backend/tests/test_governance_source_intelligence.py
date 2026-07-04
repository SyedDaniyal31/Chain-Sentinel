"""M4.2 governance source intelligence tests."""

import pytest

from app.blockchain.contract_source_provider import VerifiedContractSource
from app.blockchain.source_analysis_engine import SourceAnalysisEngine
from app.models.enums import ConfidenceLevel, GovernanceType
from app.services.governance_analyzer import GovernanceAnalyzer
from tests.test_governance_analyzer import _build_mock_web3


class FakeSourceProvider:
    def __init__(self, verified: VerifiedContractSource | None) -> None:
        self._verified = verified

    async def get_verified_source(self, contract_address: str, chain_id: int):
        return self._verified


@pytest.mark.asyncio
async def test_governance_uses_source_access_control_with_high_confidence() -> None:
    verified = VerifiedContractSource(
        contract_name="RoleToken",
        source_code="""
        contract RoleToken is AccessControl {
            bytes32 public constant MINTER_ROLE = keccak256("MINTER_ROLE");
            bytes32 public constant PAUSER_ROLE = keccak256("PAUSER_ROLE");
        }
        """,
        abi=[
            {"type": "function", "name": "grantRole", "inputs": []},
            {"type": "function", "name": "hasRole", "inputs": []},
        ],
        compiler_version="v0.8.20+commit.a1b79de6",
    )

    analyzer = GovernanceAnalyzer(
        _build_mock_web3(bytecode=b"\x60\x80"),
        chain_id=1,
        source_provider=FakeSourceProvider(verified),
        source_engine=SourceAnalysisEngine(),
    )

    result = await analyzer.analyze(
        "0x742d35cc6634c0532925a3b844bc9e7595f0beb0",
        bytecode=b"\x60\x80",
        logic_address="0x742d35cc6634c0532925a3b844bc9e7595f0beb0",
        logic_bytecode=b"\x60\x80",
        is_upgradeable=False,
        admin_address=None,
        admin_type=None,
        owner_address=None,
        owner_type=None,
        is_timelock=False,
        ownership_capability=False,
        contract_type=None,
    )

    assert result.governance_type == GovernanceType.ACCESS_CONTROL
    assert result.source_confidence == ConfidenceLevel.HIGH
    assert result.role_count >= 1


@pytest.mark.asyncio
async def test_governance_detects_renounced_ownership_from_source() -> None:
    verified = VerifiedContractSource(
        contract_name="Renounced",
        source_code="contract Renounced is Ownable { function renounceOwnership() public {} }",
        abi=[{"type": "function", "name": "renounceOwnership", "inputs": []}],
    )

    analyzer = GovernanceAnalyzer(
        _build_mock_web3(bytecode=b"\x60\x80"),
        chain_id=1,
        source_provider=FakeSourceProvider(verified),
    )

    result = await analyzer.analyze(
        "0x742d35cc6634c0532925a3b844bc9e7595f0beb0",
        bytecode=b"\x60\x80",
        logic_address="0x742d35cc6634c0532925a3b844bc9e7595f0beb0",
        logic_bytecode=b"\x60\x80",
        is_upgradeable=False,
        admin_address=None,
        admin_type=None,
        owner_address=None,
        owner_type=None,
        is_timelock=False,
        ownership_capability=True,
        contract_type=None,
    )

    assert result.ownership_renounced is True
    assert result.ownership_address is None
