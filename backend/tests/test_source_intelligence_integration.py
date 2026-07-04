"""M4.2 capability and honeypot source intelligence integration tests."""

import pytest

from app.blockchain.capability_intelligence import build_capability_inventory
from app.blockchain.contract_source_provider import VerifiedContractSource
from app.blockchain.honeypot_intelligence import build_honeypot_findings, merge_source_into_honeypot_findings
from app.blockchain.source_analysis_engine import SourceAnalysisEngine
from app.models.enums import CapabilityConfidence, CapabilityDetectionMethod, HoneypotConfidence, HoneypotDetectionMethod
from app.services.capability_analyzer import CapabilityAnalyzer
from app.services.honeypot_analyzer import HoneypotAnalyzer
from tests.test_capability_analyzer import FakeSourceProvider as CapabilityFakeSourceProvider
from tests.test_honeypot_analyzer import FakeSourceProvider as HoneypotFakeSourceProvider, TOKEN, _build_mock_web3


def test_capability_inventory_prefers_source_before_bytecode() -> None:
    verified = VerifiedContractSource(
        contract_name="Token",
        source_code="contract Token { function pause() external {} function blacklist(address) external {} }",
        abi=[
            {"type": "function", "name": "pause", "inputs": []},
            {"type": "function", "name": "blacklist", "inputs": []},
        ],
    )
    source_analysis = SourceAnalysisEngine().analyze(verified)

    inventory = build_capability_inventory(
        logic_bytecode=b"\x60\x80",
        source_analysis=source_analysis,
        source_verified=True,
    )

    assert inventory["pause"].enabled is True
    assert inventory["pause"].detection_method == CapabilityDetectionMethod.SOURCE
    assert inventory["pause"].confidence == CapabilityConfidence.HIGH
    assert inventory["blacklist"].enabled is True


def test_honeypot_merge_source_upgrades_trading_gate_finding() -> None:
    verified = VerifiedContractSource(
        contract_name="GateToken",
        source_code="contract GateToken { function enableTrading() external {} }",
        abi=[{"type": "function", "name": "enableTrading", "inputs": []}],
    )
    source_analysis = SourceAnalysisEngine().analyze(verified)
    findings = build_honeypot_findings(logic_bytecode=b"\x60\x80")
    merged = merge_source_into_honeypot_findings(findings, source_analysis)

    trading = next(f for f in merged if f.finding_type.value == "trading_gate")
    assert trading.enabled is True
    assert trading.confidence == HoneypotConfidence.HIGH
    assert trading.detection_method == HoneypotDetectionMethod.SOURCE


@pytest.mark.asyncio
async def test_capability_analyzer_uses_source_engine() -> None:
    verified = VerifiedContractSource(
        contract_name="Token",
        source_code="contract Token { function pause() external {} }",
        abi=[{"type": "function", "name": "pause", "inputs": []}],
    )
    analyzer = CapabilityAnalyzer(
        _build_mock_web3(bytecode=b""),
        chain_id=11155111,
        source_provider=CapabilityFakeSourceProvider(verified),
    )

    result = await analyzer.analyze(TOKEN, bytecode=b"\x60\x80")

    assert result.pause_capability is True
    assert result.capabilities["pause"].confidence == CapabilityConfidence.HIGH
    assert result.detection_method == CapabilityDetectionMethod.SOURCE


@pytest.mark.asyncio
async def test_honeypot_analyzer_merges_source_findings() -> None:
    verified = VerifiedContractSource(
        contract_name="GateToken",
        source_code="contract GateToken { function enableTrading() external {} function setBuyFee(uint256) external {} }",
        abi=[
            {"type": "function", "name": "enableTrading", "inputs": []},
            {"type": "function", "name": "setBuyFee", "inputs": []},
        ],
    )
    analyzer = HoneypotAnalyzer(
        _build_mock_web3(bytecode=b""),
        chain_id=11155111,
        source_provider=HoneypotFakeSourceProvider(verified),
    )

    result = await analyzer.analyze(TOKEN, bytecode=b"\x60\x80")

    assert result.trading_enabled_control is True
    assert result.transfer_tax_control is True
    assert any(
        finding.enabled and finding.detection_method == HoneypotDetectionMethod.SOURCE
        for finding in result.findings
    )
