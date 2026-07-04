"""Risk assessment schemas for rug-pull detection."""

from decimal import Decimal

from pydantic import BaseModel, Field

from app.models.enums import (
    AdminType,
    CentralizationLevel,
    ConfidenceLevel,
    ContractType,
    ProxyType,
    RiskLevel,
    ScanDetectionMethod,
    ThreatLevel,
)


class ContractRiskInput(BaseModel):
    """Contract findings consumed by RiskEngine."""

    is_contract: bool
    is_upgradeable: bool
    implementation_address: str | None
    admin_address: str | None
    admin_type: AdminType | None = None
    owner_address: str | None = None
    owner_type: AdminType | None = None
    is_timelock: bool = False
    min_delay: int | None = None
    mint_capability: bool = False
    pause_capability: bool = False
    blacklist_capability: bool = False
    ownership_capability: bool = False
    trading_enabled_control: bool = False
    whitelist_control: bool = False
    blacklist_sell_blocking: bool = False
    transfer_tax_control: bool = False
    trade_simulated: bool = False
    can_buy: bool | None = None
    can_sell: bool | None = None
    buy_tax_bps: int | None = None
    sell_tax_bps: int | None = None
    is_verified: bool = False
    contract_type: ContractType | None = None
    proxy_type: ProxyType | None = None
    detection_method: ScanDetectionMethod | None = None
    has_liquidity: bool = False
    liquidity_usd: Decimal = Decimal("0.00")
    liquidity_locked: bool = False
    liquidity_lock_percentage: Decimal = Decimal("0.00")
    lp_owner: str | None = None
    primary_dex: str | None = None
    liquidity_analyzed: bool = False
    deployer_is_fresh: bool = False
    creator_owns_majority: bool = False
    lp_owner_is_creator: bool = False
    exchange_funded_deployer: bool = False
    tornado_funded_deployer: bool = False
    treasury_is_multisig: bool = False
    wallet_known_scam: bool = False
    wallet_analyzed: bool = False


class RiskAssessment(BaseModel):
    """Rule-based rug-pull risk output."""

    risk_score: Decimal = Field(..., ge=0, le=100, description="Numeric risk score 0–100.")
    risk_level: RiskLevel
    risk_reasons: list[str] = Field(default_factory=list)
    threat_level: ThreatLevel = ThreatLevel.LOW
    centralization_level: CentralizationLevel = CentralizationLevel.LOW
    confidence_level: ConfidenceLevel = ConfidenceLevel.LOW
