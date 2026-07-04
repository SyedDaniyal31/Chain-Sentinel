"""Background scan job processor."""

import logging
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.blockchain.chain_registry import DEFAULT_CHAIN_ID, get_chain_registry
from app.blockchain.web3_provider_factory import create_web3_provider_factory
from app.core.analyzer_constants import ANALYZER_VERSION
from app.core.config import Settings, get_settings
from app.core.exceptions import ScanNotFoundError
from app.models.enums import ScanJobStatus, ScanType
from app.models.scan_job import ScanJob
from app.models.scan_result import ScanResult
from app.services.contract_analyzer import ContractAnalyzer
from app.services.risk_score import compute_mock_risk_score
from app.services.wallet_analyzer import WalletAnalyzer

logger = logging.getLogger(__name__)


class ScanWorker:
    """Executes scan jobs asynchronously and persists lifecycle transitions."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def process(self, scan_id: int) -> ScanJob:
        """
        Run the scan lifecycle for a single job.

        Transitions:
            pending → running → completed
            pending/running → failed (on unexpected error)
        """
        scan_job = await self._load_scan(scan_id)

        if scan_job.status != ScanJobStatus.PENDING:
            logger.warning(
                "Skipping scan %s — expected pending, found %s",
                scan_id,
                scan_job.status,
            )
            return scan_job

        await self._set_status(scan_job, ScanJobStatus.RUNNING)
        logger.info(
            "Scan %s started (target=%s, chain_id=%s)",
            scan_id,
            scan_job.target_address,
            scan_job.chain_id,
        )

        settings = get_settings()
        chain_id = scan_job.chain_id or DEFAULT_CHAIN_ID
        registry = get_chain_registry()
        chain = registry.get(chain_id)
        web3_factory = create_web3_provider_factory(settings)
        web3 = web3_factory.get_web3(chain_id)
        await self._capture_chain_context(scan_job, web3, chain.rpc_url)

        try:
            if scan_job.scan_type == ScanType.WALLET:
                await self._run_wallet_analyzer(scan_job, web3, chain_id)
                scan_job.risk_score = compute_mock_risk_score(
                    scan_job.scan_type,
                    scan_job.target_address,
                )
            elif scan_job.scan_type == ScanType.CONTRACT:
                scan_result = await self._run_contract_analyzer(scan_job, web3, chain_id)
                scan_job.risk_score = scan_result.risk_score

            await self._set_status(scan_job, ScanJobStatus.COMPLETED)
            logger.info(
                "Scan %s completed (risk_score=%s, chain_id=%s, block=%s)",
                scan_id,
                scan_job.risk_score,
                scan_job.chain_id,
                scan_job.block_number,
            )
        except Exception:
            await self._set_status(scan_job, ScanJobStatus.FAILED)
            logger.exception("Scan %s failed", scan_id)
            raise

        return scan_job

    async def _capture_chain_context(
        self,
        scan_job: ScanJob,
        web3,
        rpc_url: str,
    ) -> None:
        """Persist RPC endpoint, chain ID, and block height on the scan job."""
        chain_id = await web3.eth.chain_id
        block_number = await web3.eth.block_number
        scan_job.chain_id = chain_id
        scan_job.block_number = block_number
        scan_job.rpc_endpoint = rpc_url[:255]
        await self._session.flush()
        logger.info(
            "Scan %s chain context (chain_id=%s, block=%s, rpc=%s)",
            scan_job.id,
            chain_id,
            block_number,
            scan_job.rpc_endpoint,
        )

    async def _run_wallet_analyzer(
        self,
        scan_job: ScanJob,
        web3,
        chain_id: int,
    ) -> ScanResult:
        """Fetch on-chain wallet data via JSON-RPC and persist a ScanResult row."""
        analyzer = WalletAnalyzer(web3, expected_chain_id=chain_id)
        analysis = await analyzer.analyze(scan_job.target_address)

        scan_result = ScanResult(
            scan_job_id=scan_job.id,
            chain_id=analysis.chain_id,
            latest_block=analysis.latest_block,
            wallet_balance_wei=analysis.wallet_balance_wei,
            analyzer_version=ANALYZER_VERSION,
        )
        self._session.add(scan_result)
        await self._session.flush()
        logger.info(
            "Scan %s wallet analysis stored (chain_id=%s, block=%s, balance_wei=%s)",
            scan_job.id,
            analysis.chain_id,
            analysis.latest_block,
            analysis.wallet_balance_wei,
        )
        return scan_result

    async def _run_contract_analyzer(
        self,
        scan_job: ScanJob,
        web3,
        chain_id: int,
    ) -> ScanResult:
        """Fetch runtime bytecode via eth_getCode and persist contract reconnaissance."""
        analyzer = ContractAnalyzer(web3, expected_chain_id=chain_id)
        analysis = await analyzer.analyze(scan_job.target_address)

        scan_result = ScanResult(
            scan_job_id=scan_job.id,
            chain_id=analysis.chain_id,
            latest_block=analysis.latest_block,
            is_contract=analysis.is_contract,
            bytecode_size=analysis.bytecode_size,
            is_upgradeable=analysis.is_upgradeable,
            implementation_address=analysis.implementation_address,
            admin_address=analysis.admin_address,
            admin_type=analysis.admin_type,
            owner_address=analysis.owner_address,
            owner_type=analysis.owner_type,
            is_timelock=analysis.is_timelock,
            min_delay=analysis.min_delay,
            mint_capability=analysis.mint_capability,
            pause_capability=analysis.pause_capability,
            blacklist_capability=analysis.blacklist_capability,
            ownership_capability=analysis.ownership_capability,
            trading_enabled_control=analysis.trading_enabled_control,
            whitelist_control=analysis.whitelist_control,
            blacklist_sell_blocking=analysis.blacklist_sell_blocking,
            transfer_tax_control=analysis.transfer_tax_control,
            trade_simulated=analysis.trade_simulated,
            can_buy=analysis.can_buy,
            can_sell=analysis.can_sell,
            buy_tax_bps=analysis.buy_tax_bps,
            sell_tax_bps=analysis.sell_tax_bps,
            risk_score=analysis.risk_score,
            risk_level=analysis.risk_level,
            risk_reasons=analysis.risk_reasons,
            detection_method=analysis.detection_method,
            analyzer_version=analysis.analyzer_version,
            contract_type=analysis.contract_type,
            proxy_type=analysis.proxy_type,
            is_verified=analysis.is_verified,
            threat_level=analysis.threat_level,
            centralization_level=analysis.centralization_level,
            confidence_level=analysis.confidence_level,
            governance_type=analysis.governance_type,
            upgrade_authority=analysis.upgrade_authority,
            role_count=analysis.role_count,
            governance_roles=(
                [role.model_dump() for role in analysis.governance_roles]
                if analysis.governance_roles
                else None
            ),
            governance_ownership_address=analysis.governance_ownership_address,
            governance_ownership_renounced=analysis.governance_ownership_renounced,
            governance_source_confidence=analysis.governance_source_confidence,
            capability_count=analysis.capability_count,
            capabilities_detail=(
                {
                    key: detail.model_dump(mode="json")
                    for key, detail in analysis.capabilities_detail.items()
                }
                if analysis.capabilities_detail
                else None
            ),
            honeypot_score=analysis.honeypot_score,
            honeypot_risk=analysis.honeypot_risk,
            honeypot_finding_count=analysis.honeypot_finding_count,
            honeypot_is_suspected=analysis.honeypot_is_suspected,
            honeypot_is_confirmed=analysis.honeypot_is_confirmed,
            honeypot_simulation_status=analysis.honeypot_simulation_status,
            honeypot_findings=(
                [finding.model_dump(mode="json") for finding in analysis.honeypot_findings]
                if analysis.honeypot_findings
                else None
            ),
            honeypot_simulation=(
                analysis.honeypot_simulation.model_dump(mode="json")
                if analysis.honeypot_simulation
                else None
            ),
            liquidity_has_liquidity=analysis.liquidity_has_liquidity,
            liquidity_usd=analysis.liquidity_usd,
            liquidity_primary_dex=analysis.liquidity_primary_dex,
            liquidity_pair_address=analysis.liquidity_pair_address,
            liquidity_lp_owner=analysis.liquidity_lp_owner,
            liquidity_locked=analysis.liquidity_locked,
            liquidity_lock_percentage=analysis.liquidity_lock_percentage,
            liquidity_lock_expiry=analysis.liquidity_lock_expiry,
            liquidity_top_pools=(
                [pool.model_dump(mode="json") for pool in analysis.liquidity_top_pools]
                if analysis.liquidity_top_pools is not None
                else None
            ),
            wallet_creator=analysis.wallet_creator,
            wallet_deployer=analysis.wallet_deployer,
            wallet_owner=analysis.wallet_owner,
            wallet_treasury=analysis.wallet_treasury,
            wallet_funding_source=(
                analysis.wallet_funding_source.value if analysis.wallet_funding_source else None
            ),
            wallet_funding_wallet=analysis.wallet_funding_wallet,
            wallet_is_fresh_deployer=analysis.wallet_is_fresh_deployer,
            wallet_reputation_known_scam=analysis.wallet_reputation_known_scam,
            wallet_reputation_phishing=analysis.wallet_reputation_phishing,
            wallet_reputation_sanctioned=analysis.wallet_reputation_sanctioned,
            wallet_reputation_exploit_related=analysis.wallet_reputation_exploit_related,
            wallet_reputation_confidence=analysis.wallet_reputation_confidence,
            wallet_lp_owner_is_creator=analysis.wallet_lp_owner_is_creator,
            wallet_creator_owns_majority=analysis.wallet_creator_owns_majority,
            wallet_exchange_funded_deployer=analysis.wallet_exchange_funded_deployer,
            wallet_tornado_funded_deployer=analysis.wallet_tornado_funded_deployer,
            wallet_treasury_is_multisig=analysis.wallet_treasury_is_multisig,
            wallet_risk_score=analysis.wallet_risk_score,
            wallet_relationship_graph=(
                analysis.wallet_relationship_graph.model_dump(mode="json")
                if analysis.wallet_relationship_graph is not None
                else None
            ),
            protocol_intelligence=(
                analysis.protocol_intelligence.model_dump(mode="json")
                if analysis.protocol_intelligence is not None
                else None
            ),
        )
        self._session.add(scan_result)
        await self._session.flush()
        logger.info(
            "Scan %s contract analysis stored (chain_id=%s, block=%s, is_contract=%s, "
            "bytecode_size=%s, detection_method=%s, analyzer_version=%s, "
            "risk_score=%s, risk_level=%s)",
            scan_job.id,
            analysis.chain_id,
            analysis.latest_block,
            analysis.is_contract,
            analysis.bytecode_size,
            analysis.detection_method,
            analysis.analyzer_version,
            analysis.risk_score,
            analysis.risk_level,
        )
        return scan_result

    async def _load_scan(self, scan_id: int) -> ScanJob:
        result = await self._session.execute(select(ScanJob).where(ScanJob.id == scan_id))
        scan_job = result.scalar_one_or_none()
        if scan_job is None:
            raise ScanNotFoundError(scan_id)
        return scan_job

    async def _set_status(self, scan_job: ScanJob, status: ScanJobStatus) -> None:
        scan_job.status = status
        scan_job.updated_at = datetime.now(UTC)
        await self._session.flush()
