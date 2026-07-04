"""Pytest configuration and shared fixtures."""

import os

# Force in-memory SQLite for unit tests (ignore host .env Postgres URL).
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ.setdefault("DB_AUTO_CREATE_TABLES", "true")
os.environ.setdefault("APP_DEBUG", "false")
os.environ.setdefault("CHAIN_ID", "11155111")

from app.core.config import get_settings

get_settings.cache_clear()

import pytest
from decimal import Decimal
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models.enums import (
    CentralizationLevel,
    ConfidenceLevel,
    ContractType,
    GovernanceType,
    ProxyType,
    RiskLevel,
    ScanDetectionMethod,
    ThreatLevel,
    UpgradeAuthority,
)
from app.blockchain.capability_intelligence import build_capability_inventory
from app.blockchain.honeypot_intelligence import build_honeypot_findings, build_honeypot_summary
from app.blockchain.honeypot_simulation_state import build_not_run_simulation_state
from app.models.scan_result import ScanResult
from app.services.scan_worker import ScanWorker


@pytest.fixture(autouse=True)
def mock_analyzers(monkeypatch: pytest.MonkeyPatch) -> None:
    """Avoid live JSON-RPC calls in worker and API integration tests."""

    async def fake_capture_chain_context(
        worker: ScanWorker,
        scan_job: object,
        _web3: object,
        rpc_url: object,
    ) -> None:
        scan_job.chain_id = getattr(scan_job, "chain_id", None) or 11155111  # type: ignore[attr-defined]
        scan_job.block_number = 12345678  # type: ignore[attr-defined]
        scan_job.rpc_endpoint = str(rpc_url)[:255]  # type: ignore[attr-defined]
        await worker._session.flush()

    async def fake_run_wallet_analyzer(
        worker: ScanWorker,
        scan_job: object,
        _web3: object,
        _settings: object,
    ) -> ScanResult:
        scan_result = ScanResult(
            scan_job_id=scan_job.id,  # type: ignore[attr-defined]
            chain_id=11155111,
            latest_block=12345678,
            wallet_balance_wei=1000000000000000000,
            analyzer_version="1.1.0",
        )
        worker._session.add(scan_result)
        await worker._session.flush()
        return scan_result

    async def fake_run_contract_analyzer(
        worker: ScanWorker,
        scan_job: object,
        _web3: object,
        _settings: object,
    ) -> ScanResult:
        empty_capabilities = build_capability_inventory(logic_bytecode=b"")
        empty_honeypot_findings = build_honeypot_findings(logic_bytecode=b"")
        empty_honeypot_simulation = build_not_run_simulation_state()
        empty_honeypot_summary = build_honeypot_summary(
            empty_honeypot_findings,
            simulation=empty_honeypot_simulation,
        )
        scan_result = ScanResult(
            scan_job_id=scan_job.id,  # type: ignore[attr-defined]
            chain_id=11155111,
            latest_block=12345680,
            is_contract=True,
            bytecode_size=24576,
            is_upgradeable=False,
            implementation_address=None,
            admin_address=None,
            admin_type=None,
            owner_address=None,
            owner_type=None,
            is_timelock=False,
            min_delay=None,
            mint_capability=False,
            pause_capability=False,
            blacklist_capability=False,
            ownership_capability=False,
            trading_enabled_control=False,
            whitelist_control=False,
            blacklist_sell_blocking=False,
            transfer_tax_control=False,
            trade_simulated=False,
            can_buy=None,
            can_sell=None,
            buy_tax_bps=None,
            sell_tax_bps=None,
            risk_score=Decimal("0.00"),
            risk_level=RiskLevel.LOW,
            risk_reasons=["No upgradeability indicators detected"],
            detection_method=ScanDetectionMethod.BYTECODE,
            analyzer_version="1.1.0",
            contract_type=ContractType.ERC20,
            proxy_type=ProxyType.NONE,
            is_verified=False,
            threat_level=ThreatLevel.LOW,
            centralization_level=CentralizationLevel.LOW,
            confidence_level=ConfidenceLevel.MEDIUM,
            governance_type=GovernanceType.OWNABLE,
            upgrade_authority=UpgradeAuthority.NONE,
            role_count=0,
            governance_roles=[],
            governance_ownership_address=None,
            capability_count=0,
            capabilities_detail={
                key: detail.model_dump(mode="json")
                for key, detail in empty_capabilities.items()
            },
            honeypot_score=empty_honeypot_summary.honeypot_score,
            honeypot_risk=empty_honeypot_summary.honeypot_risk,
            honeypot_finding_count=empty_honeypot_summary.finding_count,
            honeypot_is_suspected=empty_honeypot_summary.is_suspected,
            honeypot_is_confirmed=empty_honeypot_summary.is_confirmed,
            honeypot_simulation_status=empty_honeypot_simulation.status,
            honeypot_findings=[
                finding.model_dump(mode="json") for finding in empty_honeypot_findings
            ],
            honeypot_simulation=empty_honeypot_simulation.model_dump(mode="json"),
        )
        worker._session.add(scan_result)
        await worker._session.flush()
        return scan_result

    monkeypatch.setattr(ScanWorker, "_capture_chain_context", fake_capture_chain_context)
    monkeypatch.setattr(ScanWorker, "_run_wallet_analyzer", fake_run_wallet_analyzer)
    monkeypatch.setattr(ScanWorker, "_run_contract_analyzer", fake_run_contract_analyzer)


@pytest.fixture
async def client() -> AsyncClient:
    """Async HTTP client with FastAPI lifespan (DB init + table creation)."""
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as http_client:
            yield http_client
