"""M4.2 SourceAnalysisEngine unit tests."""

from app.blockchain.contract_source_provider import VerifiedContractSource
from app.blockchain.source_analysis_engine import SourceAnalysisEngine
from app.models.enums import ConfidenceLevel


def test_source_engine_detects_ownable_access_control_and_pausable() -> None:
    verified = VerifiedContractSource(
        contract_name="TestToken",
        source_code="""
        contract TestToken is Ownable, AccessControl, Pausable {
            bytes32 public constant MINTER_ROLE = keccak256("MINTER_ROLE");
            function mint(address to, uint256 amount) external onlyRole(MINTER_ROLE) whenNotPaused {}
            function pause() external { _pause(); }
            function unpause() external { _unpause(); }
        }
        """,
        abi=[
            {"type": "function", "name": "owner", "inputs": []},
            {"type": "function", "name": "grantRole", "inputs": []},
            {"type": "function", "name": "pause", "inputs": []},
            {"type": "function", "name": "mint", "inputs": []},
        ],
        compiler_version="v0.8.20+commit.a1b79de6",
    )

    result = SourceAnalysisEngine().analyze(verified)

    assert result is not None
    assert result.verified is True
    assert result.source_confidence == ConfidenceLevel.HIGH
    assert result.ownable.detected is True
    assert result.access_control.detected is True
    assert result.pausable.detected is True
    assert "MINTER_ROLE" in result.role_names


def test_source_engine_detects_trading_gate_tax_blacklist_rescue() -> None:
    verified = VerifiedContractSource(
        contract_name="TaxToken",
        source_code="""
        contract TaxToken {
            function enableTrading() external {}
            function setBuyFee(uint256 fee) external {}
            function blacklist(address account) external {}
            function rescueTokens(address token) external {}
        }
        """,
        abi=[
            {"type": "function", "name": "enableTrading", "inputs": []},
            {"type": "function", "name": "setBuyFee", "inputs": []},
            {"type": "function", "name": "blacklist", "inputs": []},
            {"type": "function", "name": "rescueTokens", "inputs": []},
        ],
    )

    result = SourceAnalysisEngine().analyze(verified)

    assert result is not None
    assert result.trading_gate.detected is True
    assert result.tax_controller.detected is True
    assert result.blacklist.detected is True
    assert result.rescue_function.detected is True


def test_source_engine_detects_renounced_ownership() -> None:
    verified = VerifiedContractSource(
        contract_name="RenouncedToken",
        source_code="contract RenouncedToken is Ownable { function renounceOwnership() public {} }",
        abi=[{"type": "function", "name": "renounceOwnership", "inputs": []}],
    )

    result = SourceAnalysisEngine().analyze(
        verified,
        ownership_address="0x0000000000000000000000000000000000000000",
    )

    assert result is not None
    assert result.renounced_ownership is True


def test_source_engine_returns_none_for_unverified() -> None:
    assert SourceAnalysisEngine().analyze(None) is None
