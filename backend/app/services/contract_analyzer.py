"""Smart contract on-chain reconnaissance via JSON-RPC."""

import logging

from web3 import AsyncWeb3

from app.blockchain.capability import detect_capabilities_from_bytecode
from app.blockchain.honeypot_simulation import create_honeypot_simulation_provider
from app.blockchain.source_verification import create_contract_source_provider
from decimal import Decimal

from app.core.analyzer_constants import ANALYZER_VERSION, resolve_scan_detection_method
from app.core.config import get_settings
from app.core.exceptions import BlockchainRpcError
from app.core.validators import normalize_eth_address
from app.models.enums import AdminType, CapabilityDetectionMethod, HoneypotDetectionMethod
from app.schemas.risk import ContractRiskInput
from app.schemas.scan_result import ContractAnalysisData
from app.services.admin_analyzer import AdminAnalyzer
from app.services.admin_classifier import AdminClassifier
from app.services.capability_analyzer import CapabilityAnalyzer
from app.services.contract_classifier import ContractClassifier
from app.services.governance_analyzer import GovernanceAnalyzer
from app.services.honeypot_analyzer import HoneypotAnalyzer
from app.services.liquidity_analyzer import LiquidityAnalyzer
from app.services.wallet_intelligence_analyzer import WalletIntelligenceAnalyzer
from app.services.protocol_intelligence_analyzer import ProtocolIntelligenceAnalyzer
from app.services.protocol_relationship_analyzer import ProtocolRelationshipAnalyzer
from app.services.threat_surface_analyzer import ThreatSurfaceAnalyzer
from app.services.proxy_admin_analyzer import ProxyAdminAnalyzer
from app.services.proxy_analyzer import ProxyAnalyzer
from app.services.risk_engine import RiskEngine
from app.services.timelock_analyzer import TimelockAnalyzer

logger = logging.getLogger(__name__)


class ContractAnalyzer:
    """Collects baseline contract intelligence from an EVM JSON-RPC endpoint."""

    def __init__(
        self,
        web3: AsyncWeb3,
        expected_chain_id: int | None = None,
        proxy_analyzer: ProxyAnalyzer | None = None,
        admin_analyzer: AdminAnalyzer | None = None,
        admin_classifier: AdminClassifier | None = None,
        proxy_admin_analyzer: ProxyAdminAnalyzer | None = None,
        timelock_analyzer: TimelockAnalyzer | None = None,
        capability_analyzer: CapabilityAnalyzer | None = None,
        honeypot_analyzer: HoneypotAnalyzer | None = None,
        contract_classifier: ContractClassifier | None = None,
        governance_analyzer: GovernanceAnalyzer | None = None,
        liquidity_analyzer: LiquidityAnalyzer | None = None,
        wallet_intelligence_analyzer: WalletIntelligenceAnalyzer | None = None,
        protocol_intelligence_analyzer: ProtocolIntelligenceAnalyzer | None = None,
        protocol_relationship_analyzer: ProtocolRelationshipAnalyzer | None = None,
        threat_surface_analyzer: ThreatSurfaceAnalyzer | None = None,
        risk_engine: RiskEngine | None = None,
    ) -> None:
        self._web3 = web3
        self._expected_chain_id = expected_chain_id
        self._proxy_analyzer = proxy_analyzer or ProxyAnalyzer(web3)
        self._admin_analyzer = admin_analyzer or AdminAnalyzer(web3)
        self._admin_classifier = admin_classifier or AdminClassifier(web3)
        self._proxy_admin_analyzer = proxy_admin_analyzer or ProxyAdminAnalyzer(
            web3,
            admin_classifier=self._admin_classifier,
        )
        self._timelock_analyzer = timelock_analyzer or TimelockAnalyzer(web3)
        if capability_analyzer is not None:
            self._capability_analyzer = capability_analyzer
        else:
            settings = get_settings()
            self._capability_analyzer = CapabilityAnalyzer(
                web3,
                chain_id=expected_chain_id or settings.chain_id,
                source_provider=create_contract_source_provider(settings),
            )
        if honeypot_analyzer is not None:
            self._honeypot_analyzer = honeypot_analyzer
        else:
            settings = get_settings()
            self._honeypot_analyzer = HoneypotAnalyzer(
                web3,
                chain_id=expected_chain_id or settings.chain_id,
                source_provider=create_contract_source_provider(settings),
                simulation_provider=create_honeypot_simulation_provider(settings),
            )
        if contract_classifier is not None:
            self._contract_classifier = contract_classifier
        else:
            settings = get_settings()
            self._contract_classifier = ContractClassifier(
                web3,
                chain_id=expected_chain_id or settings.chain_id,
                source_provider=create_contract_source_provider(settings),
                timelock_analyzer=self._timelock_analyzer,
            )
        self._governance_analyzer = governance_analyzer or GovernanceAnalyzer(
            web3,
            chain_id=expected_chain_id or get_settings().chain_id,
            source_provider=create_contract_source_provider(get_settings()),
        )
        if liquidity_analyzer is not None:
            self._liquidity_analyzer = liquidity_analyzer
        else:
            self._liquidity_analyzer = LiquidityAnalyzer(
                web3,
                chain_id=expected_chain_id or get_settings().chain_id or 1,
            )
        if wallet_intelligence_analyzer is not None:
            self._wallet_intelligence_analyzer = wallet_intelligence_analyzer
        else:
            self._wallet_intelligence_analyzer = WalletIntelligenceAnalyzer(
                chain_id=expected_chain_id or get_settings().chain_id or 1,
            )
        if protocol_intelligence_analyzer is not None:
            self._protocol_intelligence_analyzer = protocol_intelligence_analyzer
        else:
            self._protocol_intelligence_analyzer = ProtocolIntelligenceAnalyzer(web3)
        if protocol_relationship_analyzer is not None:
            self._protocol_relationship_analyzer = protocol_relationship_analyzer
        else:
            self._protocol_relationship_analyzer = ProtocolRelationshipAnalyzer()
        if threat_surface_analyzer is not None:
            self._threat_surface_analyzer = threat_surface_analyzer
        else:
            self._threat_surface_analyzer = ThreatSurfaceAnalyzer()
        self._risk_engine = risk_engine or RiskEngine()

    async def analyze(self, target_address: str) -> ContractAnalysisData:
        """
        Fetch chain context, bytecode, proxy/admin/owner, and timelock metadata.

        Uses eth_getCode, eth_getStorageAt, eth_call (owner(), getMinDelay()).

        Raises:
            ValueError: Invalid address format.
            BlockchainRpcError: RPC connectivity or chain mismatch.
        """
        normalized = normalize_eth_address(target_address)
        checksum_address = AsyncWeb3.to_checksum_address(normalized)

        if not await self._web3.is_connected():
            raise BlockchainRpcError("Unable to connect to Ethereum RPC endpoint")

        try:
            chain_id = await self._web3.eth.chain_id
            latest_block = await self._web3.eth.block_number
            bytecode = await self._web3.eth.get_code(checksum_address)
        except Exception as exc:
            logger.exception("RPC call failed for contract %s", normalized)
            raise BlockchainRpcError("Ethereum RPC request failed") from exc

        if self._expected_chain_id is not None and chain_id != self._expected_chain_id:
            raise BlockchainRpcError(
                f"RPC chain_id {chain_id} does not match configured CHAIN_ID {self._expected_chain_id}"
            )

        bytecode_bytes = bytes(bytecode)
        is_contract = len(bytecode_bytes) > 0
        is_upgradeable = False
        implementation_address: str | None = None
        admin_address: str | None = None
        admin_type = None
        owner_address: str | None = None
        owner_type = None
        is_timelock = False
        min_delay: int | None = None
        mint_capability = False
        pause_capability = False
        blacklist_capability = False
        ownership_capability = False
        trading_enabled_control = False
        whitelist_control = False
        blacklist_sell_blocking = False
        transfer_tax_control = False
        can_buy: bool | None = None
        can_sell: bool | None = None
        buy_tax_bps: int | None = None
        sell_tax_bps: int | None = None
        trade_simulated = False
        capability_detection = CapabilityDetectionMethod.NONE
        honeypot_detection = HoneypotDetectionMethod.NONE
        implementation_bytecode: bytes | None = None
        governance_type = None
        upgrade_authority = None
        role_count: int | None = None
        governance_roles = None
        governance_ownership_address: str | None = None
        governance_ownership_renounced: bool | None = None
        governance_source_confidence = None
        capability_count: int | None = None
        capabilities_detail = None
        honeypot_score: int | None = None
        honeypot_risk = None
        honeypot_finding_count: int | None = None
        honeypot_is_suspected: bool | None = None
        honeypot_is_confirmed: bool | None = None
        honeypot_simulation_status = None
        honeypot_findings = None
        honeypot_simulation = None
        contract_type = None
        liquidity_has_liquidity = None
        liquidity_usd = None
        liquidity_primary_dex = None
        liquidity_pair_address = None
        liquidity_lp_owner = None
        liquidity_locked = None
        liquidity_lock_percentage = None
        liquidity_lock_expiry = None
        liquidity_top_pools = None
        wallet_creator = None
        wallet_deployer = None
        wallet_owner = None
        wallet_treasury = None
        wallet_funding_source = None
        wallet_funding_wallet = None
        wallet_is_fresh_deployer = None
        wallet_reputation_known_scam = None
        wallet_reputation_phishing = None
        wallet_reputation_sanctioned = None
        wallet_reputation_exploit_related = None
        wallet_reputation_confidence = None
        wallet_lp_owner_is_creator = None
        wallet_creator_owns_majority = None
        wallet_exchange_funded_deployer = None
        wallet_tornado_funded_deployer = None
        wallet_treasury_is_multisig = None
        wallet_risk_score = None
        wallet_relationship_graph = None
        protocol_intelligence = None

        if is_contract:
            proxy_analysis = await self._proxy_analyzer.analyze(normalized)
            is_upgradeable = proxy_analysis.is_upgradeable
            implementation_address = proxy_analysis.implementation_address

            admin_analysis = await self._admin_analyzer.analyze(normalized)
            admin_address = admin_analysis.admin_address

            if admin_address:
                admin_type = await self._admin_classifier.classify(admin_address)

            if admin_type == AdminType.CONTRACT:
                is_timelock, min_delay = await self._merge_timelock_probe(
                    admin_address,
                    is_timelock,
                    min_delay,
                )

                owner_analysis = await self._proxy_admin_analyzer.analyze(
                    admin_address,
                    admin_type,
                )
                owner_address = owner_analysis.owner_address
                owner_type = owner_analysis.owner_type

                if owner_address and owner_type == AdminType.CONTRACT:
                    is_timelock, min_delay = await self._merge_timelock_probe(
                        owner_address,
                        is_timelock,
                        min_delay,
                    )

            if implementation_address:
                try:
                    impl_checksum = AsyncWeb3.to_checksum_address(
                        normalize_eth_address(implementation_address)
                    )
                    impl_code = await self._web3.eth.get_code(impl_checksum)
                    implementation_bytecode = bytes(impl_code)
                except Exception:
                    logger.warning(
                        "Failed to fetch implementation bytecode for %s",
                        implementation_address,
                    )

            honeypot_analysis = await self._honeypot_analyzer.analyze(
                normalized,
                bytecode=bytecode_bytes,
                implementation_address=implementation_address,
                implementation_bytecode=implementation_bytecode,
            )
            trading_enabled_control = honeypot_analysis.trading_enabled_control
            whitelist_control = honeypot_analysis.whitelist_control
            blacklist_sell_blocking = honeypot_analysis.blacklist_sell_blocking
            transfer_tax_control = honeypot_analysis.transfer_tax_control
            can_buy = honeypot_analysis.can_buy
            can_sell = honeypot_analysis.can_sell
            buy_tax_bps = honeypot_analysis.buy_tax_bps
            sell_tax_bps = honeypot_analysis.sell_tax_bps
            trade_simulated = honeypot_analysis.trade_simulated
            honeypot_detection = honeypot_analysis.detection_method
            honeypot_score = honeypot_analysis.summary.honeypot_score
            honeypot_risk = honeypot_analysis.summary.honeypot_risk
            honeypot_finding_count = honeypot_analysis.summary.finding_count
            honeypot_is_suspected = honeypot_analysis.summary.is_suspected
            honeypot_is_confirmed = honeypot_analysis.summary.is_confirmed
            honeypot_simulation_status = honeypot_analysis.simulation.status
            honeypot_findings = honeypot_analysis.findings
            honeypot_simulation = honeypot_analysis.simulation

        classification = await self._contract_classifier.classify(
            normalized,
            bytecode=bytecode_bytes,
            is_contract=is_contract,
            implementation_address=implementation_address,
            implementation_bytecode=implementation_bytecode,
            admin_address=admin_address,
            is_timelock_hint=is_timelock,
        )
        contract_type = classification.contract_type

        if is_contract:
            ownership_hint = detect_capabilities_from_bytecode(
                implementation_bytecode or bytecode_bytes
            ).ownership_capability
            governance = await self._governance_analyzer.analyze(
                normalized,
                bytecode=bytecode_bytes,
                logic_address=implementation_address or normalized,
                logic_bytecode=implementation_bytecode or bytecode_bytes,
                is_upgradeable=is_upgradeable,
                admin_address=admin_address,
                admin_type=admin_type,
                owner_address=owner_address,
                owner_type=owner_type,
                is_timelock=is_timelock,
                ownership_capability=ownership_hint,
                contract_type=contract_type,
            )
            governance_type = governance.governance_type
            upgrade_authority = governance.upgrade_authority
            role_count = governance.role_count
            governance_roles = governance.roles
            governance_ownership_address = governance.ownership_address
            governance_ownership_renounced = governance.ownership_renounced
            governance_source_confidence = governance.source_confidence

            capability_analysis = await self._capability_analyzer.analyze(
                normalized,
                bytecode=bytecode_bytes,
                implementation_address=implementation_address,
                implementation_bytecode=implementation_bytecode,
                governance_roles=governance_roles,
                governance_ownership_address=governance_ownership_address,
                admin_address=admin_address,
                owner_address=owner_address,
                trade_simulated=trade_simulated,
                buy_tax_bps=buy_tax_bps,
                sell_tax_bps=sell_tax_bps,
                transfer_tax_control=transfer_tax_control,
                trading_enabled_control=trading_enabled_control,
                whitelist_control=whitelist_control,
            )
            mint_capability = capability_analysis.mint_capability
            pause_capability = capability_analysis.pause_capability
            blacklist_capability = capability_analysis.blacklist_capability
            ownership_capability = capability_analysis.ownership_capability
            capability_detection = capability_analysis.detection_method
            capability_count = capability_analysis.capability_count
            capabilities_detail = capability_analysis.capabilities
        else:
            governance_type = None
            upgrade_authority = None
            role_count = None
            governance_roles = None
            governance_ownership_address = None
            governance_ownership_renounced = None
            governance_source_confidence = None

        if is_contract:
            liquidity_analysis = await self._liquidity_analyzer.analyze(normalized)
            liquidity_has_liquidity = liquidity_analysis.has_liquidity
            liquidity_usd = liquidity_analysis.liquidity_usd
            liquidity_primary_dex = liquidity_analysis.primary_dex
            liquidity_pair_address = liquidity_analysis.pair_address
            liquidity_lp_owner = liquidity_analysis.lp_owner
            liquidity_locked = liquidity_analysis.liquidity_locked
            liquidity_lock_percentage = liquidity_analysis.liquidity_lock_percentage
            liquidity_lock_expiry = liquidity_analysis.lock_expiry
            liquidity_top_pools = liquidity_analysis.top_pools

            wallet_analysis = await self._wallet_intelligence_analyzer.analyze(
                normalized,
                admin_address=admin_address,
                admin_type=admin_type,
                owner_address=owner_address,
                owner_type=owner_type,
                governance_ownership_address=governance_ownership_address,
                is_timelock=is_timelock,
                upgrade_authority=upgrade_authority,
                lp_owner=liquidity_lp_owner,
            )
            wallet_creator = wallet_analysis.ownership.creator
            wallet_deployer = wallet_analysis.ownership.deployer
            wallet_owner = wallet_analysis.ownership.owner
            wallet_treasury = wallet_analysis.ownership.treasury
            wallet_funding_source = wallet_analysis.funding.funding_source
            wallet_funding_wallet = wallet_analysis.funding.funding_wallet
            wallet_is_fresh_deployer = wallet_analysis.deployer_is_fresh
            wallet_reputation_known_scam = wallet_analysis.reputation.known_scam
            wallet_reputation_phishing = wallet_analysis.reputation.phishing
            wallet_reputation_sanctioned = wallet_analysis.reputation.sanctioned
            wallet_reputation_exploit_related = wallet_analysis.reputation.exploit_related
            wallet_reputation_confidence = wallet_analysis.reputation.confidence
            wallet_lp_owner_is_creator = wallet_analysis.lp_owner_is_creator
            wallet_creator_owns_majority = wallet_analysis.creator_owns_majority
            wallet_exchange_funded_deployer = wallet_analysis.exchange_funded_deployer
            wallet_tornado_funded_deployer = wallet_analysis.tornado_funded_deployer
            wallet_treasury_is_multisig = wallet_analysis.treasury_is_multisig
            wallet_risk_score = wallet_analysis.wallet_risk_score
            wallet_relationship_graph = wallet_analysis.graph

            protocol_intelligence = await self._protocol_intelligence_analyzer.analyze(
                normalized,
                bytecode=bytecode_bytes,
                chain_id=chain_id,
                implementation_bytecode=implementation_bytecode,
                implementation_address=implementation_address,
                admin_address=admin_address,
                is_timelock=is_timelock,
                is_verified=classification.is_verified,
            )

            protocol_intelligence = self._protocol_relationship_analyzer.analyze(
                normalized,
                protocol_intelligence=protocol_intelligence,
                governance_type=governance_type,
                upgrade_authority=upgrade_authority,
                governance_ownership_address=governance_ownership_address,
                governance_ownership_renounced=bool(governance_ownership_renounced),
                has_timelock=is_timelock,
                is_verified=classification.is_verified,
                is_upgradeable=is_upgradeable,
                implementation_address=implementation_address,
                admin_address=admin_address,
                owner_address=owner_address,
                capabilities_detail=capabilities_detail,
                honeypot_is_suspected=bool(honeypot_is_suspected),
                liquidity_has_liquidity=bool(liquidity_has_liquidity),
                liquidity_primary_dex=liquidity_primary_dex,
                liquidity_pair_address=liquidity_pair_address,
                wallet_creator=wallet_creator,
                wallet_deployer=wallet_deployer,
                wallet_owner=wallet_owner,
                wallet_treasury=wallet_treasury,
            )

            protocol_intelligence = self._threat_surface_analyzer.analyze(
                normalized,
                protocol_intelligence=protocol_intelligence,
                governance_type=governance_type,
                upgrade_authority=upgrade_authority,
                governance_ownership_address=governance_ownership_address,
                governance_ownership_renounced=bool(governance_ownership_renounced),
                has_timelock=is_timelock,
                is_verified=classification.is_verified,
                is_upgradeable=is_upgradeable,
                implementation_address=implementation_address,
                admin_address=admin_address,
                owner_address=owner_address,
                capabilities_detail=capabilities_detail,
                mint_capability=mint_capability,
                pause_capability=pause_capability,
                honeypot_is_suspected=bool(honeypot_is_suspected),
                honeypot_is_confirmed=bool(honeypot_is_confirmed),
                liquidity_has_liquidity=bool(liquidity_has_liquidity),
                liquidity_primary_dex=liquidity_primary_dex,
                liquidity_pair_address=liquidity_pair_address,
                liquidity_usd=liquidity_usd,
                wallet_creator=wallet_creator,
                wallet_deployer=wallet_deployer,
                wallet_owner=wallet_owner,
                wallet_treasury=wallet_treasury,
                treasury_is_multisig=bool(wallet_treasury_is_multisig),
            )

        detection_method = resolve_scan_detection_method(
            capability_detection,
            honeypot_detection,
        )

        risk = self._risk_engine.evaluate_contract_risk(
            ContractRiskInput(
                is_contract=is_contract,
                is_upgradeable=is_upgradeable,
                implementation_address=implementation_address,
                admin_address=admin_address,
                admin_type=admin_type,
                owner_address=owner_address,
                owner_type=owner_type,
                is_timelock=is_timelock,
                min_delay=min_delay,
                mint_capability=mint_capability,
                pause_capability=pause_capability,
                blacklist_capability=blacklist_capability,
                ownership_capability=ownership_capability,
                trading_enabled_control=trading_enabled_control,
                whitelist_control=whitelist_control,
                blacklist_sell_blocking=blacklist_sell_blocking,
                transfer_tax_control=transfer_tax_control,
                trade_simulated=trade_simulated,
                can_buy=can_buy,
                can_sell=can_sell,
                buy_tax_bps=buy_tax_bps,
                sell_tax_bps=sell_tax_bps,
                is_verified=classification.is_verified,
                contract_type=classification.contract_type,
                proxy_type=classification.proxy_type,
                detection_method=detection_method,
                has_liquidity=bool(liquidity_has_liquidity) if is_contract else False,
                liquidity_usd=liquidity_usd or Decimal("0.00"),
                liquidity_locked=bool(liquidity_locked) if is_contract else False,
                liquidity_lock_percentage=liquidity_lock_percentage or Decimal("0.00"),
                lp_owner=liquidity_lp_owner,
                primary_dex=liquidity_primary_dex,
                liquidity_analyzed=is_contract,
                deployer_is_fresh=bool(wallet_is_fresh_deployer) if is_contract else False,
                creator_owns_majority=bool(wallet_creator_owns_majority) if is_contract else False,
                lp_owner_is_creator=bool(wallet_lp_owner_is_creator) if is_contract else False,
                exchange_funded_deployer=bool(wallet_exchange_funded_deployer) if is_contract else False,
                tornado_funded_deployer=bool(wallet_tornado_funded_deployer) if is_contract else False,
                treasury_is_multisig=bool(wallet_treasury_is_multisig) if is_contract else False,
                wallet_known_scam=bool(wallet_reputation_known_scam or wallet_reputation_sanctioned)
                if is_contract
                else False,
                wallet_analyzed=is_contract,
            )
        )

        return ContractAnalysisData(
            chain_id=chain_id,
            latest_block=latest_block,
            is_contract=is_contract,
            bytecode_size=len(bytecode_bytes),
            is_upgradeable=is_upgradeable,
            implementation_address=implementation_address,
            admin_address=admin_address,
            admin_type=admin_type,
            owner_address=owner_address,
            owner_type=owner_type,
            is_timelock=is_timelock,
            min_delay=min_delay,
            mint_capability=mint_capability,
            pause_capability=pause_capability,
            blacklist_capability=blacklist_capability,
            ownership_capability=ownership_capability,
            trading_enabled_control=trading_enabled_control,
            whitelist_control=whitelist_control,
            blacklist_sell_blocking=blacklist_sell_blocking,
            transfer_tax_control=transfer_tax_control,
            can_buy=can_buy,
            can_sell=can_sell,
            buy_tax_bps=buy_tax_bps,
            sell_tax_bps=sell_tax_bps,
            trade_simulated=trade_simulated,
            risk_score=risk.risk_score,
            risk_level=risk.risk_level,
            risk_reasons=risk.risk_reasons,
            detection_method=detection_method,
            analyzer_version=ANALYZER_VERSION,
            contract_type=classification.contract_type,
            proxy_type=classification.proxy_type,
            is_verified=classification.is_verified,
            threat_level=risk.threat_level,
            centralization_level=risk.centralization_level,
            confidence_level=risk.confidence_level,
            governance_type=governance_type,
            upgrade_authority=upgrade_authority,
            role_count=role_count,
            governance_roles=governance_roles,
            governance_ownership_address=governance_ownership_address,
            governance_ownership_renounced=governance_ownership_renounced,
            governance_source_confidence=governance_source_confidence,
            capability_count=capability_count,
            capabilities_detail=capabilities_detail,
            honeypot_score=honeypot_score,
            honeypot_risk=honeypot_risk,
            honeypot_finding_count=honeypot_finding_count,
            honeypot_is_suspected=honeypot_is_suspected,
            honeypot_is_confirmed=honeypot_is_confirmed,
            honeypot_simulation_status=honeypot_simulation_status,
            honeypot_findings=honeypot_findings,
            honeypot_simulation=honeypot_simulation,
            liquidity_has_liquidity=liquidity_has_liquidity,
            liquidity_usd=liquidity_usd,
            liquidity_primary_dex=liquidity_primary_dex,
            liquidity_pair_address=liquidity_pair_address,
            liquidity_lp_owner=liquidity_lp_owner,
            liquidity_locked=liquidity_locked,
            liquidity_lock_percentage=liquidity_lock_percentage,
            liquidity_lock_expiry=liquidity_lock_expiry,
            liquidity_top_pools=liquidity_top_pools,
            wallet_creator=wallet_creator,
            wallet_deployer=wallet_deployer,
            wallet_owner=wallet_owner,
            wallet_treasury=wallet_treasury,
            wallet_funding_source=wallet_funding_source,
            wallet_funding_wallet=wallet_funding_wallet,
            wallet_is_fresh_deployer=wallet_is_fresh_deployer,
            wallet_reputation_known_scam=wallet_reputation_known_scam,
            wallet_reputation_phishing=wallet_reputation_phishing,
            wallet_reputation_sanctioned=wallet_reputation_sanctioned,
            wallet_reputation_exploit_related=wallet_reputation_exploit_related,
            wallet_reputation_confidence=wallet_reputation_confidence,
            wallet_lp_owner_is_creator=wallet_lp_owner_is_creator,
            wallet_creator_owns_majority=wallet_creator_owns_majority,
            wallet_exchange_funded_deployer=wallet_exchange_funded_deployer,
            wallet_tornado_funded_deployer=wallet_tornado_funded_deployer,
            wallet_treasury_is_multisig=wallet_treasury_is_multisig,
            wallet_risk_score=wallet_risk_score,
            wallet_relationship_graph=wallet_relationship_graph,
            protocol_intelligence=protocol_intelligence,
        )

    async def _merge_timelock_probe(
        self,
        contract_address: str,
        is_timelock: bool,
        min_delay: int | None,
    ) -> tuple[bool, int | None]:
        """Apply timelock detection; owner-level probe overrides prior admin-level values."""
        analysis = await self._timelock_analyzer.analyze(contract_address)
        if analysis.is_timelock:
            return True, analysis.min_delay
        return is_timelock, min_delay
